<?php $menu = 'settings'; ?>
<?php include 'include/head.php'; ?>
<?php

if (!isset($_SESSION['user'])) {
	die('Страница недоступна');
}

$sth = $dbh->prepare('select * from user order by name');
$sth->execute();

$users = [];

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$users[] = $row;
}
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Настройки</h1>
</div>

<p>
	На странице можно корректировать некоторые настройки AllSky.
</p>
<p>
	На сегодняшний момент основная масса настроек находится в файле <a href="https://github.com/oleg-milantiev/allsky.py/blob/master/config.py.dist" target="_blank">/opt/allsky.py/config.py</a>
</p>

<div class="card">
	<div class="card-body">
		<h5 class="card-title">Пользователи</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-users">

			<table class="table table-stripped">
				<thead>
					<tr>
						<th>E-Mail</th>
						<th>Имя</th>
						<th>Пароль</th>
					</tr>
				</thead>
				<tbody>
					<?php foreach ($users as $user): ?>
						<tr>
							<td><?php echo $user['email']?></td>
							<td>
								<input class="form-control" type="text" value="<?php echo $user['name']; ?>" name="name[<?php echo $user['id']; ?>]">
							</td>
							<td>
								<input class="form-control" type="password" value="<?php echo $user['password']; ?>" name="password[<?php echo $user['id']; ?>]">
							</td>
						</tr>
					<?php endforeach; ?>
				</tbody>
			</table>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>
	</div>
</div>

<br><br>

<div class="card">
	<div class="card-body">
		<h5 class="card-title">Настройки</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings">

			<div class="form-group">
				<label>Мощность обогрева подкупольного:</label>
				<select class="form-control" name="hotPercent">
					<option value="">- отключено -</option>
					<?php for ($i = 10; $i <= 100; $i += 10):?>
						<option value="<?php echo $i; ?>"<?php echo (isset($config['web']['hotPercent']) and ($config['web']['hotPercent'] == $i)) ? ' selected' : '' ?>><?php echo $i; ?>%</option>
					<?php endfor; ?>
				</select>
			</div>

			<div class="form-group">
				<label>Счётчик (HTML-код на всех страницах, сразу после открывающегося тега body):</label>
				<textarea class="form-control" name="counter"><?php echo $config['web']['counter']; ?></textarea>
			</div>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>
	</div>
</div>

<?php include 'include/tail.php'; ?>
