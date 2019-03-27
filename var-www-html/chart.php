<?php $menu = 'chart'; ?>
<?php include 'include/head.php'; ?>

<?php
$types = [
	'temperature'     => 'Температура',
	'humidity'        => 'Влажность',
	'pressure'        => 'Давление',
	'voltage'         => 'Напряжение',
	'wind-speed'      => 'Скорость ветра',
	'wind-direction'  => 'Напр. ветра',
	'sky-temperature' => 'Темп. неба',
	'ccd-exposure'    => 'CCD выдержка',
	'ccd-average'     => 'CCD среднее',
];

$type = $_GET['type'];

if (!isset($types[ $type ])) {
	$type = array_keys($types)[0];
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
$period = $_GET['period'];

if (!isset($periods[ $period ])) {
	$period = array_keys($periods)[0];
}

$labels = [];
$data = [];


$sth = $dbh->prepare('select date, val from sensor where channel = :channel and type = :type and date > :date order by date asc');

$sth->execute([
	'date'    => time() - $periodTime[$period],
	'type'    => $type,
	'channel' => 0, // @todo
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
	<?php foreach ($types as $key => $name):?>
		<div style="float: left; width: 130px">
			<a href="?type=<?php echo $key; ?>&period=<?php echo $period?>" class="btn btn-<?php echo ($key == $type) ? 'success' : 'info';?> btn-sm"><?php echo $name;?></a>
		</div>
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

$(document).ready(function() {
  // Graphs
  var ctx = document.getElementById('myChart')
  // eslint-disable-next-line no-unused-vars
  var myChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: <?php echo json_encode($labels); ?>,
      datasets: [{
        data: <?php echo json_encode($data); ?>,
        backgroundColor: 'transparent',
        borderColor: '#007bff',
        borderWidth: 4,
        pointBackgroundColor: '#007bff'
      }]
    },
    options: {
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
  })
});

</script>

<?php include 'include/tail.php'; ?>
