<!doctype html>
<?php
// @todo вынос в отдельный файл, общий с /root/allsky.py
$config = [
	'name' => 'Борис Кудрявцев',
];

$stat = stat('current.jpg');
$date = date('d/m/Y H:i', $stat['ctime']);

?>
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
	<a class="navbar-brand col-sm-3 col-md-2 mr-0" href="#">AllSky - <?php echo $config['name']; ?></a>
	<!-- <input class="form-control form-control-dark w-100" type="text" placeholder="Search" aria-label="Search"> -->
	<ul class="navbar-nav px-3">
		<li class="nav-item text-nowrap">
			<a class="nav-link" href="#" onclick="alert('Скоро!')">Вход</a>
		</li>
	</ul>
</nav>

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
				</ul>

<!--				<h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
					<span>Saved reports</span>
					<a class="d-flex align-items-center text-muted" href="#">
						<span data-feather="plus-circle"></span>
					</a>
				</h6>
				<ul class="nav flex-column mb-2">
					<li class="nav-item">
						<a class="nav-link" href="#">
							<span data-feather="file-text"></span>
							Current month
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link" href="#">
							<span data-feather="file-text"></span>
							Last quarter
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link" href="#">
							<span data-feather="file-text"></span>
							Social engagement
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link" href="#">
							<span data-feather="file-text"></span>
							Year-end sale
						</a>
					</li> -->
				</ul>
			</div>
		</nav>

		<main role="main" class="col-md-9 ml-sm-auto col-lg-10 px-4">
