<?php
session_start();

$config = json_decode(`/opt/allsky.py/config.json.py`, true);

$dbh = new PDO(
	'mysql:dbname='. $config['db']['database'] .';host='. $config['db']['host'],
	$config['db']['user'],
	$config['db']['passwd']);

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
	<nav class="navbar navbar-dark fixed-top bg-dark flex-md-nowrap p-0 shadow">
	<a class="navbar-brand col-sm-3 col-md-2 mr-0" href="/">AllSky - <?php echo $config['name']; ?></a>
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
					<?php endif; ?>
				</ul>

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
