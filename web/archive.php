<?php $menu = 'archive'; ?>
<?php include 'include/head.php'; ?>
<?php

$snapDir = scandir($config['path']['jpg'], SCANDIR_SORT_DESCENDING);

$days = [];
foreach ($snapDir as $item) {
	if (preg_match('#^(\d\d\d\d-\d\d-\d\d)#', $item, $out)) {
		$days[ $out[1] ] = true;
	}
}

$date = null;

if (isset($_GET['date'])) {
	if (
		preg_match('#(\d\d)\.(\d\d)\.(\d\d\d\d) (\d\d):(\d\d)#', $_GET['date'], $out) and
		in_array($out[3] .'-'. $out[2] .'-'. $out[1] .'_'. $out[4] .'-'. $out[5] .'.jpg', $snapDir)
	) {
		$date = $out[3] .'-'. $out[2] .'-'. $out[1] .'_'. $out[4] .'-'. $out[5] .'.jpg';
	}
}
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
				<a class="nav-link" href="keogram.php">Кеограммы</a>
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

<div class="well">
	<h4>Последние изображения с камеры</h4>
	<div class="row">
		<div class="col-lg-3 text-center">
			<div class="datepicker"></div>
		</div>
		<div class="col-lg-6 text-center">
			<img class="snap" src="/snap/<?php echo $date ? $date : $snapDir[0]?>" style="width:100%"><br>
			<span class="snap"><?php echo $date ? $date : $snapDir[0]?></span>
		</div>
		<div class="col-lg-3 text-center">
			<button class="btn btn-lg btn-success left">&lt;</button>
			<button <?php if (!$date or ($date and array_search($date, $snapDir) == 0)): ?>disabled="disabled" <?php endif;?>class="btn btn-lg btn-success right">&gt;</button>
		</div>
	</div>
</div>

<div class="modal snap" tabindex="-1" role="dialog">
  <div class="modal-dialog" role="document" style="max-width: 1400px">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Фото из архива - <a href="#" target="_blank"></a></h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body">
        <img src="" width="1350">
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Закрыть</button>
      </div>
    </div>
  </div>
</div>




<script>
	var snapDir = <?php echo json_encode($snapDir); ?>;
	var days = <?php echo json_encode(array_keys($days)); ?>;
	var snap = <?php echo $date ? array_search($date, $snapDir) : 0; ?>;

	$(document).ready(function() {
		$('.datepicker').datepicker({
			endDate: new Date(),
			startDate: new Date(days[ days.length - 1 ]),
			beforeShowDay: function(date) {
				return (days.indexOf(
						date.getFullYear() +'-'+
						( '0'+ (date.getMonth()+1) ).slice(-2) +'-'+
						( '0'+ date.getDate() ).slice(-2)
					) != -1);
			},
			format: 'dd.mm.yyyy'
		}).on('changeDate', function(e) {
			var day = e.date.getFullYear() +'-'+
				( '0'+ (e.date.getMonth()+1) ).slice(-2) +'-'+
				( '0'+ e.date.getDate() ).slice(-2);

			for (i = 0; i < snapDir.length; i++) {
				if (snapDir[i].substr(0, 10) == day) {
					snap = i;
					update();
					return;
				}
			}
		});

		$('img.snap').click(function() {
			$('.modal.snap .modal-body img').prop('src', $(this).prop('src'));
			$('.modal.snap .modal-title a')
				.prop('href', $(this).prop('src') )
				.html( $(this).prop('src') );

			$('.modal.snap').modal('show');
		});

		$('.btn.left').click(function(e) {
			e.preventDefault();

			snap++;

			update();
		});

		$('.btn.right').click(function(e) {
			e.preventDefault();

			if (snap > 0) {
				snap--;

				update();
			}
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

<style>
	td.exitst > a {
		background: #E50104!important;
		color: #fff!important;
	}
</style>

<?php include 'include/tail.php'; ?>
