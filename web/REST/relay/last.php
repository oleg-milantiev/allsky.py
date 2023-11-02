<?php
include '../base.php';

$ret = [];

if (isset($_GET['type']) and isset($_GET['channel'])) {
	$type    = $_GET['type'];
	$channel = (int) $_GET['channel'];

	$sth = $dbh->prepare('select date, val from sensor where channel = :channel and type = :type order by id desc limit 1');

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
	$sth = $dbh->prepare('select type, channel from sensor group by type, channel');
	$sth->execute();

	$sth2 = $dbh->prepare('select date, val from sensor where channel = :channel and type = :type order by id desc limit 1');

	$ret = [];

	while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
		$sth2->execute([
			'type'    => $row['type'],
			'channel' => $row['channel'],
		]);

		if (!! ($row2 = $sth2->fetch(PDO::FETCH_ASSOC))) {
			$ret[] = [
				'type'    => $row['type'],
				'channel' => (int) $row['channel'],
				'date'    => (int) $row2['date'],
				'val'     => (double) $row2['val'],
			];
		}
	}

	RESTshow($ret, true);
}
