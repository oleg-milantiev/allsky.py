<?php
include '../base.php';

$ret = [];

$sth = $dbh->prepare('select * from sensor_last');
$sth->execute();

$ret['date'] = null;

# todo не ясно, что делать с channel. Discover?
while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	if (!$ret['date'] or $ret['date'] < $row['date']) {
		$ret['date'] = $row['date'];
	}

	$ret[ str_replace('-', '_', $row['type']) ] = $row['val'];
}

echo json_encode($ret);