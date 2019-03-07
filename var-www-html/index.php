<?php $menu = 'current'; ?>
<?php include 'include/head.php'; ?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Сейчас <span style="color: gray; font-size: 22px">(по состоянию на <?php echo $date; ?>)</span></h1>
	<!--
	<div class="btn-toolbar mb-2 mb-md-0">
		<div class="btn-group mr-2">
			<button type="button" class="btn btn-sm btn-outline-secondary">Share</button>
			<button type="button" class="btn btn-sm btn-outline-secondary">Export</button>
		</div>
		<button type="button" class="btn btn-sm btn-outline-secondary dropdown-toggle">
			<span data-feather="calendar"></span>
			This week
		</button>
	</div>
	-->
</div>

<div class="row">
	<div class="col-lg-12">
		<img style="width:100%" src="current.jpg?date=<?php echo $date; ?>">
	</div>
</div>


<?php include 'include/tail.php'; ?>
