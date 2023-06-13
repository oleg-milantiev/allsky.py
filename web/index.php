<?php $menu = 'current'; ?>
<?php include 'include/head.php'; ?>

<?php
$current = file_exists('snap/current.jpg') ? stat('snap/current.jpg') : null;

$videoDir = scandir($config['path']['video'], SCANDIR_SORT_DESCENDING);
$video    = (count($videoDir) > 3) ? stat($config['path']['video']. $videoDir[0]) : null;
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<?php if ($video):?>
		<span class="">
			последнее видео: <a target="_blank" href="/video/<?php echo $videoDir[0]; ?>"><?php echo $videoDir[0]; ?> от <?php echo date('d/m/Y H:i', $video['ctime']);?></a>
		</span>
	<?php endif?>
	<?php if ($current):?>
		<h1 class="h2 text-right">
			Сейчас <span style="color: gray; font-size: 22px">(по состоянию на <?php echo date('d/m/Y H:i', $current['ctime']); ?>)</span>
			<input type="checkbox" title="Автообновление" class="auto-refresh">
		</h1>
	<?php endif?>
</div>

<?php if ($current):?>
	<div class="row">
		<div class="col-lg-12">
			<img style="width:100%" src="snap/current.jpg?date=<?php echo $current['ctime']; ?>">
		</div>
	</div>
<?php endif?>

<script>
	var reloadTimer;

	$(document).ready(function() {
		$('input.auto-refresh').click(function() {
			localStorage['auto-refresh'] = $(this).prop('checked');
			
			refreshIfNeeded();
		});

		$('input.auto-refresh').prop('checked', (localStorage['auto-refresh'] == 'true') );

		refreshIfNeeded();
	});
	
	function refreshIfNeeded()
	{
		if ($('input.auto-refresh').prop('checked')) {
			reloadTimer = setTimeout(function() {
				document.location.href = '?time='+ new Date().getTime();
			}, 60000);
		}
		else {
			if (reloadTimer) {
				clearTimeout(reloadTimer);
			}
		}
	}
</script>

<?php include 'include/tail.php'; ?>
