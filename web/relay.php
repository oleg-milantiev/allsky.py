<?php $menu = 'relay'; ?>
<?php include 'include/head.php'; ?>
<?php

if (!isset($_SESSION['user'])) {
	echo 'Страница недоступна';

	include 'include/tail.php';

	exit;
}

$relays = [];

foreach ($config['relay'] as $relay) {
	$relays[ $relay['gpio'] ] = intval(trim(file_get_contents('/sys/class/gpio/gpio'. $relay['gpio'] .'/value')));
}
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Реле</h1>
</div>

<p>
	На странице можно управлять несколькими реле / мосфетами / ключами / .., подключенными к мини-компьютеру.
</p>

<div class="row">
	<?php foreach ($config['relay'] as $relay): ?>
		<div class="col-lg-2 text-center">
			<a href="#" rel="<?php echo $relay['gpio']; ?>" class="btn btn-<?php echo $relays[ $relay['gpio'] ] ? 'success': 'danger'?> relay">
				<span data-feather="power"></span>
				<?php echo $relay['name']; ?>
			</a>
		</div>
	<?php endforeach; ?>
</div>

<p style="padding-top: 50px">
	Настройка реле в файле <a href="https://github.com/oleg-milantiev/allsky.py/blob/master/config.py.dist" target="_blank">/opt/allsky.py/config.py</a>.<br>
</p>


<script>
	$(document).ready(function(){
		$('a.relay').click(function(e){
			e.preventDefault();
			
			if (confirm(
				'Вы уверены, что хотите '+
				($(this).hasClass('btn-success') ? 'ВЫКЛЮЧИТЬ' : 'ВКЛЮЧИТЬ' ) +
				' реле "'+ $(this).text().trim() +'"?'
			)) {

				$.post('', {
					'action': 'relay',
					'gpio':   $(this).attr('rel'),
					'state':  $(this).hasClass('btn-success') ? 0 : 1
				}, function(data){
					
					document.location.reload();
					
				}, 'json');
			}
		});
	})
</script>

<?php include 'include/tail.php'; ?>
