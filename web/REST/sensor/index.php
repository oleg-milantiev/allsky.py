<?php
include '../base.php';

$ret = [];

$sth = $dbh->prepare('select type, channel from sensor group by type, channel');
$sth->execute();

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	if (!isset($ret[ $row['type'] ])) {
		$ret[ $row['type'] ] = [];
	}

	$ret[ $row['type'] ][] = (int) $row['channel'];
}

RESTshow($ret, true);