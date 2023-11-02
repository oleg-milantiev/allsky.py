<?php $menu = 'archive'; ?>
<?php include 'include/head.php'; ?>
<?php

$videoDir = scandir('/var/www/html/video-demand/', SCANDIR_SORT_DESCENDING);

$sth = $dbh->prepare('select * from video where work_end = 0 order by work_queue desc');
$sth->execute();

$demand = [];

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$demand[] = $row;
}
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
				<a class="nav-link " href="video-day.php">Видео за ночь</a>
			</li>
			<li class="nav-item">
				<a class="nav-link active" href="#">Видео за час</a>
			</li>
		</ul>
	</div>
</div>

<?php if (isset($_SESSION['user'])): ?>
	<div class="card">
		<div class="card-body text-center">
			<form method="post">
				<input type="hidden" name="action" value="video-demand">
				<button type="submit" class="btn btn-success">Запросить видео за последний час</button>
			</form>
		</div>
	</div>

	<?php if (count($demand)): ?>
		<div class="card">
			<div class="card-body">
				<h5 class="card-title">Очередь обработки запросов</h5>
				<table class="table table-stripped">
					<thead>
						<tr>
							<th>В очереди</th>
							<th>Кодируется</th>
							<th>Начало</th>
							<th>Конец</th>
						</tr>
					</thead>
					<tbody>
						<?php foreach ($demand as $row):?>
							<tr>
								<td><?php echo date('d.m.Y H:i:s', $row['work_queue']); ?></td>
								<td><?php echo $row['work_begin'] ? date('d.m.Y H:i:s', $row['work_begin']) : 'в очереди'; ?></td>
								<td><?php echo date('d.m.Y H:i:s', $row['video_begin']); ?></td>
								<td><?php echo date('d.m.Y H:i:s', $row['video_end']); ?></td>
							</tr>
						<?php endforeach;?>
					</tbody>
				</table>
			</div>
		</div>
	<?php endif; ?>
<?php endif; ?>

<div class="card">
	<div class="card-body">
		<h5 class="card-title">Список готовых запрошенных видео-файлов</h5>
		<ul>
			<?php foreach ($videoDir as $video):?>
				<?php if (substr($video, -4) == '.mp4'):?>
				<li><a href="/video-demand/<?php echo $video?>" target="_blank"><?php echo $video?></a></li>
				<?php endif;?>
			<?php endforeach;?>
		</ul>
	</div>
</div>

<?php include 'include/tail.php'; ?>
