<?php

$stat = stat('current.jpg');
$date = date('d/m/Y H:i', $stat['ctime']);
?>
<div>
	<img src="current.jpg?date=<?php echo $date; ?>">
</div>

<div style="text-align: center">
	По состоянию на <?php echo $date; ?>
</div>
