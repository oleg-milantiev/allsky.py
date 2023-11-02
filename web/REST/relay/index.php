<?php
include '../base.php';

if (!isset($_SESSION['user'])) {
#	die('Страница недоступна');
}

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
	if (!isset($_POST['gpio']) or !isset($_POST['state'])) {
		RESTshow('Не заданы GPIO или STATE параметры', false);
	}

	file_put_contents('/sys/class/gpio/gpio'. intval($_POST['gpio']) .'/value', intval($_POST['state']) );

	RESTshow([
		'gpio'  => intval($_POST['gpio']),
		'state' => intval(trim(file_get_contents('/sys/class/gpio/gpio'. intval($_POST['gpio']) .'/value'))),
	], true);
}
else {
	$ret = [];

	foreach ($config['relay'] as $relay) {
		$ret[ $relay['gpio'] ] = [
			'name'  => $relay['name'],
			'state' => intval(trim(file_get_contents('/sys/class/gpio/gpio'. $relay['gpio'] .'/value')))
		];
	}

	RESTshow($ret, true);
}

