<?php

if (php_sapi_name() !== 'cli') {
	die('CLI only');
}

$config = json_decode(file_get_contents('/opt/allsky.py/camera/common/config.py.json'), true);

$dbh = new PDO(
	'mysql:dbname='. $config['db']['database'] .';host='. $config['db']['host'],
	$config['db']['user'],
	$config['db']['passwd']);

$sth = $dbh->prepare('select * from config');
$sth->execute();

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$config[ $row['id'] ] = json_decode($row['val'], true);
}

echo "Opening relays GPIO ports for output\n";

foreach ($config['relays'] as $relay) {
	file_put_contents('/sys/class/gpio/export', (int) $relay['gpio']);
}

sleep(1);

foreach ($config['relays'] as $relay) {
	file_put_contents('/sys/class/gpio/gpio'. intval($relay['gpio']) .'/direction', 'out');
}

sleep(1);

$sth = $dbh->prepare('select id, state from relay');
$sth->execute();

$states = [];

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$states[ $row['id'] ] = $row['state'];
}

echo "Setting initial relays GPIO state\n";
foreach ($config['relays'] as $relay) {
	echo '+ set relay '. $relay['gpio'] .' to '. ($states[ (int) $relay['gpio'] ] ?? 0) ."\n";
	file_put_contents('/sys/class/gpio/gpio'. intval($relay['gpio']) .'/value', $states[ (int) $relay['gpio'] ] ?? 0);
}
