<?php
include '../base.php';

$ret = [];

if (isset($_GET['type']) and isset($_GET['channel'])) {
	$type    = $_GET['type'];
	$channel = (int) $_GET['channel'];

	$sth = $dbh->prepare('select date, val from sensor_last where channel = :channel and type = :type limit 1');

	$sth->execute([
		'type'    => $type,
		'channel' => $channel,
	]);

	if (! ($row = $sth->fetch(PDO::FETCH_ASSOC))) {
		RESTshow('Нет данных по заданному типу и каналу', false);
	}

	RESTshow([
		'date'  => $row['date'],
		'value' => $row['val'],
	], true);
}
else {
	$sth = $dbh->prepare('select date, val, type, channel from sensor_last');
	$sth->execute();

	$ret = [];

	while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
		$ret[] = [
			'type'    => $row['type'],
			'channel' => (int) $row['channel'],
			'date'    => (int) $row['date'],
			'val'     => (double) $row['val'],
		];
	}

	RESTshow($ret, true);
}
