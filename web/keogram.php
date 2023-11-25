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

		<div class="row">
		<?php foreach ($keoDir as $keo):?>
			<?php if (substr($keo, -4) == '.jpg'):?>
				<div class="col-3">
				<a href="/keogram/<?php echo $keo?>" data-toggle="lightbox" data-gallery="gallery" class="col-md-4 text-center">
					<img src="/thumbnail.php?folder=keogram&file=<?php echo $keo?>" class="img-fluid rounded"><br>
					<?php echo $keo; ?>
				</a>
				</div>
			<?php endif;?>
		<?php endforeach;?>
		</div>
	</div>
</div>


<div class="container">
	<div class="row">
	</div>
</div>

<script>
	$(document).on("click", '[data-toggle="lightbox"]', function(event) {
		event.preventDefault();
		$(this).ekkoLightbox();
	});
</script>

<style>
	.row {
		margin: 15px;
	}
</style>

<script src="/js/ekko-lightbox.min.js"></script>


<?php include 'include/tail.php'; ?>
