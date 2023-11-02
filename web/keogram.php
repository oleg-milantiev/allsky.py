<?php $menu = 'archive'; ?>
<?php include 'include/head.php'; ?>
<?php

$keoDir = scandir('/var/www/html/keogram/', SCANDIR_SORT_DESCENDING);
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Архив</h1>
</div>

<div class="row">
	<div class="col-lg-12">
		<ul class="nav nav-tabs">
			<li class="nav-item">
				<a class="nav-link" href="archive.php">Сегодня</a>
			</li>
			<li class="nav-item">
				<a class="nav-link active" href="#">Кеограммы</a>
			</li>
			<li class="nav-item">
				<a class="nav-link" href="video-day.php">Видео за ночь</a>
			</li>
			<li class="nav-item">
				<a class="nav-link" href="video-demand.php">Видео за час</a>
			</li>
		</ul>
	</div>
</div>

<div class="card">
	<div class="card-body">
		<h5 class="card-title">Список последних кеограмм</h5>
		<ul>
			<?php foreach ($keoDir as $keo):?>
				<?php if (substr($keo, -4) == '.jpg'):?>
				<li><a href="/keogram/<?php echo $keo?>" target="_blank"><?php echo $keo?></a></li>
				<?php endif;?>
			<?php endforeach;?>
		</ul>
	</div>
</div>

<?php include 'include/tail.php'; ?>
