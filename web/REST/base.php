<?php
session_start();

$statConfig = stat('/opt/allsky.py/config.py');
$statJSON   = stat('/opt/allsky.py/config.py.json');

if (!isset($statJSON['mtime']) or !$statJSON['size'] or ($statJSON['mtime'] < $statConfig['mtime'])) {
	`/opt/allsky.py/config.json.py`;
}

$config = json_decode(file_get_contents('/opt/allsky.py/config.py.json'), true);


$dbh = new PDO(
	'mysql:dbname='. $config['db']['database'] .';host='. $config['db']['host'],
	$config['db']['user'],
	$config['db']['passwd']);

$config['web'] = [];

$sth = $dbh->prepare('select * from config');
$sth->execute();

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$config['web'][ $row['id'] ] = json_decode($row['val'], true);
}

function RESTshow($data, $success = true)
{
	if ($success) {
		echo json_encode([
			'success' => $success,
			'data'    => $data,
		]);
	}
	else {
		echo json_encode([
			'success' => $success,
			'message' => $data,
		]);
	}

	exit;
}