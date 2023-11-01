<?php
$fields = ['ccd-date', 'temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average', 'ccd-gain', 'ccd-bin', 'stars-count', 'ai-clear', 'ai-cloud'];

if (!isset($_GET['key']) or !in_array($_GET['key'], $fields)) {
	header('HTTP/1.1 500 Bad Parameters');
	exit;
}

include '../base.php';

$ret = [];

$sth = $dbh->prepare(($_GET['key'] === 'ccd-date') ? 'select date as ret from sensor where channel = 0 order by id desc limit 1' : 'select val as ret from sensor where type = "'. $_GET['key'] .'" and channel = 0 order by id desc limit 1');
$sth->execute();

if ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	echo $row['ret'];
	exit;
}

header('HTTP/1.1 404 Key not found');
exit;