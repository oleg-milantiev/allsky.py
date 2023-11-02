<?php $menu = 'archive'; ?>
<?php include 'include/head.php'; ?>
<?php

$videoDir = scandir($config['path']['video'], SCANDIR_SORT_DESCENDING);
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
				<a class="nav-link" href="keogram.php">Кеограммы</a>
			</li>
			<li class="nav-item">
				<a class="nav-link active" href="#">Видео за ночь</a>
			</li>
			<li class="nav-item">
				<a class="nav-link" href="video-demand.php">Видео за час</a>
			</li>
		</ul>
	</div>
</div>

<div class="card">
	<div class="card-body">
		<h5 class="card-title">Список последних видео-файлов за сутки</h5>
		<ul>
			<?php foreach ($videoDir as $video):?>
				<?php if (substr($video, -4) == '.mp4'):?>
				<li><a href="/video/<?php echo $video?>" target="_blank"><?php echo $video?></a></li>
				<?php endif;?>
			<?php endforeach;?>
		</ul>
	</div>
</div>

<?php include 'include/tail.php'; ?>
