<?php $menu = 'relay'; ?>
<?php include 'include/head.php'; ?>
<?php

if (!isset($_SESSION['user'])) {
	die('Страница недоступна');
}
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Реле</h1>
</div>

<p>
	На странице можно управлять несколькими реле, подключенными к мини-компьютеру.
</p>

<div class="row">
	<div class="col-lg-2 text-center">
		<a href="#" class="btn btn-danger relay">
			<span data-feather="power"></span>
			Реле 1
		</a>
	</div>
	<div class="col-lg-2 text-center">
		<a href="#" class="btn btn-danger relay">
			<span data-feather="power"></span>
			Реле 2
		</a>
	</div>
	<div class="col-lg-2 text-center">
		<a href="#" class="btn btn-danger relay">
			<span data-feather="power"></span>
			Реле 3
		</a>
	</div>
	<div class="col-lg-2 text-center">
		<a href="#" class="btn btn-danger relay">
			<span data-feather="power"></span>
			Реле 4
		</a>
	</div>
</div>

<p style="padding-top: 50px">
	Настройка реле в файле <a href="https://github.com/oleg-milantiev/allsky.py/blob/master/config.py.dist" target="_blank">/root/allsky.py/config.py</a>.<br>
	Внимание: В данный момент раздел разрабатывается и предоставлен в демонстрационных целях.
</p>


<script>
	$(document).ready(function(){
		$('a.relay').click(function(e){
			e.preventDefault();
			
			alert('... скоро на экранах страны');
		});
	})
</script>

<?php include 'include/tail.php'; ?>
