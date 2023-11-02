<?php
$fields = ['ccd-date', 'temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average', 'ccd-gain', 'ccd-bin', 'stars-count', 'ai-clear', 'ai-cloud'];

if (!isset($_GET['key']) or !in_array($_GET['key'], $fields)) {
	header('HTTP/1.1 500 Bad Parameters');
	exit;
}

include '../base.php';

$ret = [];

$sth = $dbh->prepare('select date as ret from sensor where channel = 0 order by id desc limit 1');
$sth->execute();
$date = ($row = $sth->fetch(PDO::FETCH_ASSOC)) ? $row['ret'] : null;

if ($_GET['key'] === 'ccd-date') {
	if ($date) {
		echo $date;
	}
	else {
		header('HTTP/1.1 404 Key not found');
	}

	exit;
}

$sth = $dbh->prepare('select date, val from sensor where type = "'. $_GET['key'] .'" and channel = 0 order by id desc limit 1');
$sth->execute();

if (!($row = $sth->fetch(PDO::FETCH_ASSOC))) {
	header('HTTP/1.1 404 Key not found');
	exit;
}

# Надо выдавать данные датчиков с поправкой на date. Т.к. старый датчик не актуален. А сейчас в заббиксе всё ещё пишет stars-count = 1. Но датчику уже несколько часов отроду
# добавил проверку на актуальность 10 минут
# если старше, то датчик выдаёт 0

echo (($row['date'] + 600) > time())
	? (substr($_GET['key'], 0, 3) === 'ai-') ? $row['val'] * 100 : $row['val']
	: 0;