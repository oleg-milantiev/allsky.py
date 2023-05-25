<?php
session_start();

$statConfig = stat('/opt/allsky.py/config.py');
$statJSON   = stat('/opt/allsky.py/config.py.json');

if (!isset($statJSON['mtime']) or !$statJSON['size'] or ($statJSON['mtime'] < $statConfig['mtime'])) {
	`/opt/allsky.py/config.json.py`;
}

$config = json_decode(file_get_contents('/opt/allsky.py/config.py.json'), true);

$dbh = new PDO(
	'mysql:dbname='. $config['db']['database'] .';host='. $config['db']['host'],
	$config['db']['user'],
	$config['db']['passwd']);

$sth = $dbh->prepare('select * from config');
$sth->execute();

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
    if (in_array($row['id'], ['web', 'ccd', 'processing', 'publish', 'archive', 'sensors', 'relays'])) {
		$config[ $row['id'] ] = json_decode($row['val'], true);
    }
}

if (isset($_GET['action'])) {
	switch ($_GET['action']) {
		case 'logout':
			unset($_SESSION['user']);
			break;
	}
	
	header('Location: /?time='. time());
}

if ( ($_SERVER['REQUEST_METHOD'] == 'POST') and isset($_POST['action']) ) {
	switch ($_POST['action']) {
		case 'relay':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['gpio']) or
				!isset($_POST['state']) or
				!strlen($_POST['gpio']) or
				!strlen($_POST['state'])
			) {
				die('Страница недоступна');
			}
			
			foreach ($config['relay'] as $relay) {
				if ($relay['gpio'] == $_POST['gpio']) {
					$file = '/sys/class/gpio/gpio'. $relay['gpio'] .'/value';
					
					file_put_contents(
						$file,
						$_POST['state'] ? '1' : '0'
					);
					
					$sth = $dbh->prepare('replace into relay (id, state, date) values (:id, :state, :date)');
					
					$sth->execute([
						'id'    => $relay['name'],
						'state' => $_POST['state'],
						'date'  => time(),
					]);
					
					echo json_encode([
						'status' => 200,
						'gpio'   => $_POST['gpio'],
						'state'  => trim(file_get_contents($file)),
					]);
					exit;
				}
			}
			
			die('Реле не найдено');

		case 'settings-users':
			if (!isset($_SESSION['user'])) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('select * from user order by name');
			$sth->execute();

			while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
				if (
					isset($_POST['name'][ $row['id'] ]) and
					isset($_POST['password'][ $row['id'] ])
				) {
					$sth2 = $dbh->prepare('update user set name = :name, password = :password where id = :id');
					$sth2->execute([
						'id'       => $row['id'],
						'name'     => $_POST['name'][ $row['id'] ],
						'password' => $_POST['password'][ $row['id'] ],
					]);
				}
			}

			header('Location: /settings.php?time='. time());
			exit;

		case 'settings-web':
			if (
				!isset($_SESSION['user']) or
                !isset($_POST['name']) or
				!isset($_POST['counter'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'web',
				'val' => json_encode([
					'name' => $_POST['name'],
					'counter' => $_POST['counter'],
				]),
			]);

			header('Location: /settings.php?tab=web&time='. time());
			exit;

	    case 'settings-ccd':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['binning']) or
				!isset($_POST['bits']) or
				!isset($_POST['avgMin']) or
				!isset($_POST['avgMax']) or
				!isset($_POST['center']) or
				!isset($_POST['expMin']) or
				!isset($_POST['expMax']) or
				!isset($_POST['gainMin']) or
				!isset($_POST['gainMax']) or
				!isset($_POST['gainStep'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'ccd',
				'val' => json_encode([
					'binning' => (int) $_POST['binning'],
					'bits' => (int) $_POST['bits'],
					'avgMin' => (int) $_POST['avgMin'],
					'avgMax' => (int) $_POST['avgMax'],
					'center' => (int) $_POST['center'],
					'expMin' => (float) $_POST['expMin'],
					'expMax' => (int) $_POST['expMax'],
					'gainMin' => (int) $_POST['gainMin'],
					'gainMax' => (int) $_POST['gainMax'],
					'gainStep' => (int) $_POST['gainStep'],
				]),
			]);
			header('Location: /settings.php?tab=ccd&time='. time());
			exit;

		case 'settings-processing':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['left']) or
				!isset($_POST['right']) or
				!isset($_POST['top']) or
				!isset($_POST['bottom']) or
				!isset($_POST['logoX']) or
				!isset($_POST['logoY']) or
				!isset($_POST['wb'])
			) {
				die('Страница недоступна');
			}

			$val = [
				'crop' => [
					'left' => (int) $_POST['left'],
					'right' => (int) $_POST['right'],
					'top' => (int) $_POST['top'],
					'bottom' => (int) $_POST['bottom'],
				],
				'logo' => [
					'x' => (int) $_POST['logoX'],
					'y' => (int) $_POST['logoY'],
				],
				'annotation' => $_POST['annotation'],
				'wb' => [
					'type' => $_POST['wb'],
					'r' => $_POST['r'],
					'g' => $_POST['g'],
					'b' => $_POST['b'],
				],
			];

			if (isset($_FILES['file']['error']) and
				($_FILES['file']['error'] === 0) and
				is_file($_FILES['file']['tmp_name']) and
				in_array($_FILES['file']['type'], ['image/jpeg', 'image/png'])
			) {
				foreach (['jpeg', 'png'] as $ext) {
					$filename = $config['path']['web'] .'/logo.'. $ext;
					if (file_exists($filename)) {
						unlink($filename);
					}
				}

				$filename = 'logo.'. explode('/', $_FILES['file']['type'])[1];
				copy($_FILES['file']['tmp_name'], $config['path']['web'] .'/'. $filename);
				$val['logo']['file'] = $filename;
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'processing',
				'val' => json_encode($val),
			]);

			header('Location: /settings.php?tab=processing&time='. time());
			exit;

		case 'settings-publish':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['jpg'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'publish',
				'val' => json_encode([
					'jpg' => $_POST['jpg'],
				]),
			]);

			header('Location: /settings.php?tab=publish&time='. time());
			exit;

		case 'settings-relay':
			if (
				!isset($_SESSION['user'])
			) {
				die('Страница недоступна');
			}


			$relays = [];

			if (isset($_POST['relays']) and
				is_array($_POST['relays']) ) {

				foreach ($_POST['relays'] as $relay) {
					if (!$relay['name'] or ((int)$relay['gpio'] < 0)) {
						continue;
					}

					$relays[] = [
						'name'   => $relay['name'],
						'gpio'   => (int)$relay['gpio'],
						'hotter' => $relay['hotter'] === 'обогрев',
						'temp'   => (float)$relay['temp'],
					];
				}
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'relays',
				'val' => json_encode($relays),
			]);

			header('Location: /settings.php?tab=relays&time='. time());
			exit;

		case 'settings-archive':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['jpg']) or
				!isset($_POST['fit']) or
				!isset($_POST['sensors']) or
				!isset($_POST['video'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'archive',
				'val' => json_encode([
					'jpg' => (int) $_POST['jpg'],
					'fit' => (int) $_POST['fit'],
					'sensors' => (int) $_POST['sensors'],
					'video' => (int) $_POST['video'],
				]),
			]);

			header('Location: /settings.php?tab=archive&time='. time());
			exit;

		case 'settings-sensors':
			if (
				!isset($_SESSION['user']) or
				!isset($_POST['bme280']) or
				!is_array($_POST['bme280']) or
				!isset($_POST['ads1115']) or
				!is_array($_POST['ads1115'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('replace into config (id, val) values (:id, :val)');
			$sth->execute([
				'id'  => 'sensors',
				'val' => json_encode([
					'bme280' => [
						0 => ['name' => $_POST['bme280'][0]['name'] ?? ''],
						1 => ['name' => $_POST['bme280'][1]['name'] ?? ''],
					],
					'ads1115' => [
						0 => [
							'name' => $_POST['ads1115'][0]['name'] ?? '',
							'divider' => $_POST['ads1115'][0]['divider'] ?? '',
						],
						1 => [
							'name' => $_POST['ads1115'][1]['name'] ?? '',
							'divider' => $_POST['ads1115'][1]['divider'] ?? '',
						],
					]
				]),
			]);

			header('Location: /settings.php?tab=sensors&time='. time());
			exit;

		case 'video-demand':
			if (
				!isset($_SESSION['user'])
			) {
				die('Страница недоступна');
			}

			$sth = $dbh->prepare('insert into video (job, work_queue, video_begin, video_end) values (:job, :work_queue, :video_begin, :video_end)');
			$sth->execute([
				'job'         => gearman,
				'work_queue'  => time(),
				'video_begin' => time() - 3600,
				'video_end'   => time(),
			]);

			`/usr/bin/gearman -b -f video-demand 0`;

			header('Location: /video-demand.php?time='. time());
			exit;

		case 'login':
			if (
				!isset($_POST['email']) or
				!isset($_POST['password']) or
				!$_POST['email'] or
				!$_POST['password']
			) {
				break;
			}

			$sth = $dbh->prepare('select * from user where email = :email and password = :password');
			
			$sth->execute([
				'email'    => $_POST['email'],
				'password' => $_POST['password'],
			]);
			
			$user = $sth->fetch(PDO::FETCH_ASSOC);
			
			if (!isset($user['id'])) {
				break;
			}
			
			$_SESSION['user'] = $user;
			break;
	}

	header('Location: /?time='. time());
}

// @todo переделаю на общий лог событий потом
$sth = $dbh->prepare('select * from relay order by date desc');
$sth->execute();

$log = [];

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$log[] = $row;
}


$sensors = [];

if (
	isset($config['sensors']['bme280']) and
	is_array($config['sensors']['bme280']) and
	count($config['sensors']['bme280'])
	) {

	$typeNames = [
		'temperature' => 'Температура',
		'humidity'    => 'Влажность',
		'pressure'    => 'Давление',
	];

	foreach ($config['sensors']['bme280'] as $channel => $channelName) {
		foreach (['temperature', 'humidity', 'pressure'] as $type) {
			$sth = $dbh->prepare('select * from sensor where channel = :channel and type = :type order by date desc limit 1');
			$sth->execute([
				'type'    => $type,
				'channel' => $channel,
			]);

			if ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
				$sensors[ $typeNames[$row['type']] ][ $channelName ] = [
					'date' => $row['date'],
					'val'  => $row['val'],
				];
			}
		}
	}
}

?><!doctype html>
<html lang="en">
	<head>
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
		<meta name="description" content="">
		<meta name="author" content="Mark Otto, Jacob Thornton, and Bootstrap contributors">
		<meta name="generator" content="Jekyll v3.8.5">
		<title>AllSky - <?php echo $config['name']; ?></title>

		<link rel="canonical" href="https://getbootstrap.com/docs/4.3/examples/dashboard/">

		<!-- Bootstrap core CSS -->
		<link href="/css/bootstrap.min.css" rel="stylesheet">
		<link href="/css/bootstrap-datepicker.min.css" rel="stylesheet">
        <link href="/css/bootstrap-colorpicker.min.css" rel="stylesheet">

		<script src="https://code.jquery.com/jquery-3.3.1.min.js" crossorigin="anonymous"></script>
		<script>window.jQuery || document.write('<script src="/js/vendor/jquery-3.3.1.min.js"><\/script>')</script>

		<style>
			.bd-placeholder-img {
				font-size: 1.125rem;
				text-anchor: middle;
				-webkit-user-select: none;
				-moz-user-select: none;
				-ms-user-select: none;
				user-select: none;
			}

			@media (min-width: 768px) {
				.bd-placeholder-img-lg {
					font-size: 3.5rem;
				}
			}
		</style>
		<!-- Custom styles for this template -->
		<link href="/css/allsky.css" rel="stylesheet">
	</head>


<body>
	<?php echo $config['web']['counter'] ?? ''; ?>
	<nav class="navbar navbar-dark fixed-top bg-dark flex-md-nowrap p-0 shadow">
	<a class="navbar-brand col-sm-3 col-md-2 mr-0" href="/">AllSky - <?php echo $config['web']['name']; ?></a>
	<div class="d-block d-md-none">
		<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent15" aria-controls="navbarSupportedContent15" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
	</div>
	<!-- <input class="form-control form-control-dark w-100" type="text" placeholder="Search" aria-label="Search"> -->
	
	<?php if (isset($_SESSION['user'])):?>
		<span class="text-info">Добро пожаловать, <?php echo $_SESSION['user']['name']?></span>
	<?php endif;?>

	<ul class="navbar-nav px-3">
		<li class="nav-item text-nowrap">
			<?php if (isset($_SESSION['user'])):?>
				<a class="nav-link" href="?action=logout" >Выход</a>
			<?php else:?>
				<a class="nav-link" href="#" data-toggle="modal" data-target="#modal-login">Вход</a>
			<?php endif;?>
		</li>
	</ul>
	
	<div class="collapse p-0 navbar-collapse navbar navbar-dark bg-dark shadow" id="navbarSupportedContent15">
		<ul class="navbar-nav mr-auto">
			<li class="nav-item">
				<a class="nav-link<?php if ($menu == 'current'): ?> active<?php endif; ?>" href="/">
					<span data-feather="home"></span>
					Сейчас <span class="sr-only">(current)</span>
				</a>
			</li>
			<li class="nav-item">
				<a class="nav-link<?php if ($menu == 'archive'): ?> active<?php endif; ?>" href="/archive.php">
					<span data-feather="layers"></span>
					Архив
				</a>
			</li>
			<li class="nav-item">
				<a class="nav-link<?php if ($menu == 'chart'): ?> active<?php endif; ?>" href="/chart.php">
					<span data-feather="bar-chart-2"></span>
					Графики
				</a>
			</li>
			<?php if (isset($_SESSION['user'])):?>
				<li class="nav-item">
					<a class="nav-link<?php if ($menu == 'relay'): ?> active<?php endif; ?>" href="/relay.php">
						<span data-feather="power"></span>
						Реле
					</a>
				</li>
				<li class="nav-item">
					<a class="nav-link<?php if ($menu == 'settings'): ?> active<?php endif; ?>" href="/settings.php">
						<span data-feather="settings"></span>
						Настройки
					</a>
				</li>
			<?php endif; ?>
		</ul>
	</div>

</nav>


<div class="modal" id="modal-login" tabindex="-1" role="dialog">
	<div class="modal-dialog" role="document">
		<div class="modal-content">
			<form method="post">
				<input type="hidden" name="action" value="login">
				<div class="modal-header">
					<h5 class="modal-title">Авторизация</h5>
					<button type="button" class="close" data-dismiss="modal" aria-label="Close">
						<span aria-hidden="true">&times;</span>
					</button>
				</div>
				<div class="modal-body">
					<div class="form-group">
						<label for="login-email">E-Mail</label>
						<input id="login-email" type="text" name="email" class="form-control">
					</div>
					<div class="form-group">
						<label for="login-password">Пароль</label>
						<input id="login-password" type="password" name="password" class="form-control">
					</div>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-secondary" data-dismiss="modal">Закрыть</button>
					<button type="submit" class="btn btn-primary">Войти</button>
				</div>
			</form>
		</div>
	</div>
</div>

<div class="container-fluid">
	<div class="row">
		<nav class="col-md-2 d-none d-md-block bg-light sidebar">
			<div class="sidebar-sticky">
				<ul class="nav flex-column">
					<li class="nav-item">
						<a class="nav-link<?php if ($menu == 'current'): ?> active<?php endif; ?>" href="/">
							<span data-feather="home"></span>
							Сейчас <span class="sr-only">(current)</span>
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link<?php if ($menu == 'archive'): ?> active<?php endif; ?>" href="/archive.php">
							<span data-feather="layers"></span>
							Архив
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link<?php if ($menu == 'chart'): ?> active<?php endif; ?>" href="/chart.php">
							<span data-feather="bar-chart-2"></span>
							Графики
						</a>
					</li>
					<?php if (isset($_SESSION['user'])):?>
						<li class="nav-item">
							<a class="nav-link<?php if ($menu == 'relay'): ?> active<?php endif; ?>" href="/relay.php">
								<span data-feather="power"></span>
								Реле
							</a>
						</li>
						<li class="nav-item">
							<a class="nav-link<?php if ($menu == 'settings'): ?> active<?php endif; ?>" href="/settings.php">
								<span data-feather="settings"></span>
								Настройки
							</a>
						</li>
					<?php endif; ?>
				</ul>

				<?php if (count($sensors)):?>
					<h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
						<span>Сенсоры</span>
					</h6>
					<ul class="nav flex-column mb-2">
						<?php foreach ($sensors as $type => $channels): ?>
							<?php foreach ($channels as $channel => $sensor): ?>
								<li class="nav-item">
									<a class="nav-link" href="#" title="Данные от <?php echo date('d.m.Y H:i', $sensor['date']); ?>">
										<span data-feather="file-text"></span>
										<?php echo $type ?>/<?php echo $channel ?>:
										<?php echo round($sensor['val'], 1); ?>
									</a>
								</li>
							<?php endforeach; ?>
						<?php endforeach; ?>
					</ul>
				<?php endif; ?>
				
				<?php if (isset($_SESSION['user'])):?>
					<h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
						<span>Недавние события</span>
					</h6>
					<ul class="nav flex-column mb-2">
						<?php foreach ($log as $item): ?>
							<li class="nav-item">
								<a class="nav-link" href="#">
									<span data-feather="file-text"></span>
									Реле <?php echo $item['id']?> 
									<?php if ($item['state']): ?>
										<span class="bg-success">включено</span>
									<?php else:?>
										<span class="bg-danger">выключено</span>
									<?php endif; ?>
									в <?php echo date('d.m.Y H:i', $item['date']); ?>
								</a>
							</li>
						<?php endforeach; ?>
					</ul>
				<?php endif; ?>
				
			</div>
		</nav>

		<main role="main" class="col-md-9 ml-sm-auto col-lg-10 px-4">
