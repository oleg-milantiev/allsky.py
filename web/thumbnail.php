<?php

$sizes = [150];
$size = $sizes[0];

if (isset($_GET['size'])) {

	if (!in_array((int) $_GET['size'], $sizes)) {
		die('Not allowed size');
	}

	$size = (int) $_GET['size'];
}

$folders = ['keogram'];

if (!isset($_GET['folder']) or !in_array($_GET['folder'], $folders)) {
	die('Not allowed folder');
}
$folder = $_GET['folder'];

$dst = $folder .'/'. $size .'/'. $_GET['file'];

if (!file_exists('/var/www/html/'. $dst)) {
	if (!file_exists('/var/www/html/'. $folder .'/'. $size)) {
		mkdir('/var/www/html/'. $folder .'/'. $size);
	}

	$src = '/var/www/html/'. $folder .'/'. $_GET['file'];

	$new_width = $size;
	$new_height = $size;
	list($old_width, $old_height) = getimagesize($src);

	$new_image = imagecreatetruecolor($new_width, $new_height);
	$old_image = imagecreatefromjpeg($src);

	imagecopyresampled($new_image, $old_image, 0, 0, 0, 0, $new_width, $new_height, $old_width, $old_height);

	imagejpeg($new_image, $dst);
	imagedestroy($old_image);
	imagedestroy($new_image);
}

header('Location: /'. $dst);
