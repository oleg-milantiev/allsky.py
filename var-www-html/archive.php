<?php $menu = 'archive'; ?>
<?php include 'include/head.php'; ?>
<?php

$snapDir = scandir('/var/www/html/snap/', SCANDIR_SORT_DESCENDING);
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Архив</h1>
</div>

<div class="row">
	<div class="col-lg-12">
		<ul class="nav nav-tabs">
		<li class="nav-item">
			<a class="nav-link active" href="#">Сегодня</a>
		</li>
		<li class="nav-item">
			<a class="nav-link" href="video.php">Видео</a>
		</li>
		</ul>
	</div>
</div>

<div class="well">
	<h4>Последние изображения с камеры</h4>
	<div class="row">
		<div class="col-lg-3 text-center ">
			<button class="btn btn-lg btn-success left">&lt;</button>
		</div>
		<div class="col-lg-6 text-center">
			<img class="snap" src="/snap/<?php echo $snapDir[0]?>" style="width:90%"><br>
			<span class="snap"><?php echo $snapDir[0]?></span>
		</div>
		<div class="col-lg-3 text-center">
			<button disabled="disabled" class="btn btn-lg btn-success right">&gt;</button>
		</div>
	</div>
</div>

<script>
	var snapDir = <?php echo json_encode($snapDir); ?>;
	var snap = 0;

	$(document).ready(function() {
		$('.btn.left').click(function(e) {
			e.preventDefault();

			snap++;
			
			update();
		});

		$('.btn.right').click(function(e) {
			e.preventDefault();
			
			snap--;
			
			update();
		});
		
		$(document).keydown(function(e) {
			switch(e.which) {
				case 37: // left
					$('.btn.left').click();
					break;

				case 39: // right
					$('.btn.right').click();
					break;

				default: return; // exit this handler for other keys
			}
			e.preventDefault(); // prevent the default action (scroll / move caret)
		});
	});

	function update()
	{
		$('img.snap').attr('src', '/snap/'+ snapDir[snap]);
		$('span.snap').html(snapDir[snap]);
		
		$('.btn.left').prop('disabled', (snap == snapDir.length) ? 'disabled' : null);
		$('.btn.right').prop('disabled', (snap == 0) ? 'disabled' : null);
	}
</script>

<?php include 'include/tail.php'; ?>
