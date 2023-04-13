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

<ul class="nav nav-tabs">
    <li class="nav-item">
        <a class="nav-link active" data-toggle="tab" href="#users">Пользователи</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#web">Веб</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#ccd">Камера</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#processing">Обработка</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#sensors">Сенсоры</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#relays">Реле</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-toggle="tab" href="#archive">Архив</a>
    </li>
</ul>

<div class="tab-content">
    <div class="tab-pane fade show active" id="users">
        <h5 class="card-title">Пользователи</h5>

        <form method="POST">

            <input type="hidden" name="action" value="settings-users">

            <table class="table table-stripped">
                <thead>
                <tr>
                    <th>E-Mail</th>
                    <th>Роль</th>
                    <th>Имя</th>
                    <th>Пароль</th>
                </tr>
                </thead>
                <tbody>
				<?php foreach ($users as $user): ?>
                    <tr>
                        <td><?php echo $user['email']?></td>
                        <td>Администратор</td>
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

            <div class="row">
                <div class="col-6">
                    <button class="btn btn-success btn-lg" type="submit">Сохранить</button>
                </div>
                <div class="col-6 text-right">
                    <button class="btn btn-info btn-lg button-add">Добавить</button>
                </div>
                <script>
                    $(function (){
                        $('.button-add').click(function (){
                            alert('Функция добавления пользователя ещё недоступна');
                        });
                    });
                </script>
            </div>
        </form>
    </div>

    <div class="tab-pane fade" id="web">
        <form method="POST">

            <input type="hidden" name="action" value="settings-web">

            <div class="form-group">
                <label>Счётчик (HTML-код на всех страницах, сразу после открывающегося тега body):</label>
                <textarea class="form-control" name="counter"><?php echo $config['web']['counter']; ?></textarea>
            </div>

            <button class="btn btn-success btn-lg" type="submit">Сохранить</button>
        </form>
    </div>

    <div class="tab-pane fade" id="ccd">
        Камера
    </div>

    <div class="tab-pane fade" id="processing">
        Обработка
    </div>

    <div class="tab-pane fade" id="sensors">
        Сенсоры
    </div>

    <div class="tab-pane fade" id="relays">
        <form method="POST">

            <input type="hidden" name="action" value="settings-relay">

            <div class="form-group">
                <label>Мощность обогрева подкупольного:</label>
                <select class="form-control" name="hotPercent">
                    <option value="">- отключено -</option>
					<?php for ($i = 10; $i <= 100; $i += 10):?>
                        <option value="<?php echo $i; ?>"<?php echo (isset($config['web']['hotPercent']) and ($config['web']['hotPercent'] == $i)) ? ' selected' : '' ?>><?php echo $i; ?>%</option>
					<?php endfor; ?>
                </select>
            </div>

            <button class="btn btn-success btn-lg" type="submit">Сохранить</button>
        </form>
    </div>

    <div class="tab-pane fade" id="archive">
        Архив
    </div>
</div>

<?php include 'include/tail.php'; ?>
