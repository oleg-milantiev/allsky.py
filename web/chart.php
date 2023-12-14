<?php $menu = 'chart'; ?>
<?php include 'include/head.php'; ?>

<?php
$typeChannel = [];

$typeChannel['voltage']         = ['Напряжение'];
$typeChannel['wind-speed']      = ['Скорость ветра'];
$typeChannel['wind-direction']  = ['Напр. ветра'];
$typeChannel['sky-temperature'] = ['Темп. неба'];
$typeChannel['ccd-exposure']    = ['CCD выдержка'];
$typeChannel['ccd-average']     = ['CCD среднее'];
$typeChannel['ccd-gain']        = ['CCD gain'];
$typeChannel['ccd-bin']         = ['CCD bin'];
$typeChannel['stars-count']     = ['Количество звёзд'];
$typeChannel['ai-cloud']        = ['ИИ облачность'];
$typeChannel['ai-clear']        = ['ИИ чистое небо'];

if (isset($config['sensors']['bme280'])) {
	$typeChannel['humidity']    = [];
	$typeChannel['pressure']    = [];
	$typeChannel['temperature'] = [];

	foreach ($config['sensors']['bme280'] as $id => $row) {
		if (isset($row['name']) and $row['name']) {
			$typeChannel['temperature'][$id] = 'Температура/'. $name;
			$typeChannel['humidity'][$id]    = 'Влажность/'. $name;
			$typeChannel['pressure'][$id]    = 'Давление/'. $name;
		}
	}
}
else {
	$typeChannel['humidity']    = ['Влажность'];
	$typeChannel['pressure']    = ['Давление'];
	$typeChannel['temperature'] = ['Температура'];
}


$typeChannelExists = [];

$sth = $dbh->prepare('select type, channel from sensor group by type, channel');
$sth->execute();

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$typeChannelExists[ $row['type'] ][ $row['channel'] ] = true;
}

$type = $_GET['type'] ?? '';
$channel = (int) ($_GET['channel'] ?? 0);

if (!isset($typeChannel[ $type ][ $channel ])) {
	foreach ($typeChannel as $typeItem => $channels) {
		foreach ($channels as $channelItem => $name) {
			if (isset($typeChannelExists[$typeItem][$channelItem])) {
				$type    = $typeItem;
				$channel = $channelItem;

				break;
			}
		}
	}

	if (!isset($typeChannel[ $type ][ $channel ])) {
		echo 'Нет данных для построения графиков'; exit;
	}
}

$periods = [
	'hour'  => 'Час',
	'day'   => 'Сутки',
	'week'  => 'Неделя',
	'month' => 'Месяц',
];
$periodTime = [
	'hour'  => 60 * 60,
	'day'   => 60 * 60 * 24,
	'week'  => 60 * 60 * 24 * 7,
	'month' => 60 * 60 * 24 * 30,
];
$period = $_GET['period'] ?? '';

if (!isset($periods[ $period ])) {
	$period = array_keys($periods)[0];
}

$labels = [];
$data   = [];

$fromTime = time() - $periodTime[$period];
$frame = floor($periodTime[$period] / 200);

$sth = $dbh->prepare("select tm * ". $frame ." as date, av as val from (select floor(date / ". $frame .") tm, avg(val) av from sensor where channel = :channel and type = :type and date > :date group by 1 order by date asc) z");

$sth->execute([
	'date'    => (int) $fromTime,
	'type'    => $type,
	'channel' => $channel,
]);

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$labels[] = date('d.m.Y H:i', $row['date']);
	$data[]   = $row['val'];
}
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Графики</h1>
</div>

<div class="row">
	<div class="col-lg-12">
		<ul class="nav nav-tabs">
			<li class="nav-item">
				<a class="nav-link active" href="#">Сенсоры</a>
			</li>
		</ul>
	</div>
</div>

<br>
<div class="">
	<?php foreach ($typeChannel as $typeItem => $channels):?>
		<?php foreach ($channels as $channelItem => $name): ?>
			<?php if (isset($typeChannelExists[$typeItem][$channelItem])):?>
				<div style="float: left; width: 150px">
					<a href="?type=<?php echo $typeItem; ?>&channel=<?php echo $channelItem; ?>&period=<?php echo $period?>" class="btn btn-<?php echo (($typeItem == $type) and ($channel == $channelItem)) ? 'success' : 'info';?> btn-sm"><?php echo $name;?></a>
				</div>
			<?php endif;?>
		<?php endforeach; ?>
	<?php endforeach;?>
</div>

<br><br>
<div class="">
	<?php foreach ($periods as $key => $name):?>
		<div style="float: left; width: 130px">
			<a href="?type=<?php echo $type; ?>&period=<?php echo $key?>" class="btn btn-<?php echo ($key == $period) ? 'success' : 'info';?> btn-sm"><?php echo $name;?></a>
		</div>
	<?php endforeach;?>
</div>

<br><br>

<canvas class="my-4 w-100" id="myChart" width="900" height="380"></canvas>

<script>

/* globals Chart:false, feather:false */

var chart = {
	type: 'line',
	data: {
		labels: <?php echo json_encode($labels); ?>,
		datasets: [{
			label: '<?php echo $typeChannel[ $type ][ $channel ]; ?>',
			data: <?php echo json_encode($data); ?>,
			backgroundColor: 'transparent',
			borderColor: '#007bff',
			borderWidth: 4,
			pointBackgroundColor: '#007bff',
			trendlineLinear: {
				style: "rgb(43 ,66 ,255, 0.3)",
				lineStyle: "dotted|solid",
				width: 1
			}
		}]
	},
	options: {
//		tooltips: {
//			callbacks: {
//				label: function(tooltipItem, data) {
//					console.log(tooltipItem);
//					console.log(data);
//				}
//			}
//		},

		scales: {
			yAxes: [{
				ticks: {
					beginAtZero: false
				}
			}]
		},
		legend: {
			display: false
		}
	}
};

$(document).ready(function() {
	var ctx = document.getElementById('myChart')

	var myChart = new Chart(ctx, chart);

	<?php if (in_array($type, ['ccd-exposure', 'ccd-average', 'ccd-gain',  'ccd-bin',  'stars-count',  'ai-cloud',  'ai-clear'])):?>
		ctx.onclick = function(evt){
			var activePoint = myChart.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);

			if (activePoint) {
				window.open('/archive.php?date='+ chart.data.labels[activePoint[0].index]);
			}
		};
	<?php endif;?>
});

</script>

<?php include 'include/tail.php'; ?>
