<?php $menu = 'settings'; ?>
<?php include 'include/head.php'; ?>
<?php

if (!isset($_SESSION['user'])) {
	echo 'Страница недоступна';

	include 'include/tail.php';

	exit;
}

$sth = $dbh->prepare('select * from user order by name');
$sth->execute();

$users = [];

while ($row = $sth->fetch(PDO::FETCH_ASSOC)) {
	$users[] = $row;
}

$tab = $_GET['tab'] ?? 'users';
?>

<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">

	<h1 class="h2">Настройки</h1>
</div>

<ul class="nav nav-tabs">
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'users' ? ' active' : ''; ?>" data-toggle="tab" href="#users">Пользователи</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'web' ? ' active' : ''; ?>" data-toggle="tab" href="#web">Веб</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'ccd' ? ' active' : ''; ?>" data-toggle="tab" href="#ccd">Камера</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'processing' ? ' active' : ''; ?>" data-toggle="tab" href="#processing">Обработка</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'publish' ? ' active' : ''; ?>" data-toggle="tab" href="#publish">Публикация</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'sensors' ? ' active' : ''; ?>" data-toggle="tab" href="#sensors">Датчики</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'relays' ? ' active' : ''; ?>" data-toggle="tab" href="#relays">Реле</a>
	</li>
	<li class="nav-item">
		<a class="nav-link<?php echo $tab === 'archive' ? ' active' : ''; ?>" data-toggle="tab" href="#archive">Архив</a>
	</li>
</ul>

<div class="tab-content">
	<div class="tab-pane fade<?php echo $tab === 'users' ? ' show active' : ''; ?>" id="users">
		<br>
		<h5 class="card-title">Пользователи</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-users">

			<table class="table table-stripped users">
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

	<div class="tab-pane fade<?php echo $tab === 'web' ? ' show active' : ''; ?>" id="web">
		<br>
		<h5 class="card-title">Настройки веб</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-web">

			<div class="form-group">
				<label>Название обсерватории:</label>
				<input class="form-control" type="text" name="name" value="<?php echo $config['web']['name'] ?? ''; ?>">
			</div>

			<div class="form-group">
				<label>Счётчик (HTML-код на всех страницах, сразу после открывающегося тега body):</label>
				<textarea class="form-control" name="counter"><?php echo $config['web']['counter'] ?? ''; ?></textarea>
			</div>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>
	</div>

	<div class="tab-pane fade<?php echo $tab === 'ccd' ? ' show active' : ''; ?>" id="ccd">
		<br>
		<h5 class="card-title">Настройки камеры</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-ccd">

			<div class="form-group">
				<label>Биннинг:</label>
				<div>
					<label>
						<input type="radio" name="binning" value="1"<?php echo (!isset($config['ccd']['binning']) or (isset($config['ccd']['binning']) and ($config['ccd']['binning'] === 1))) ? ' checked' : ''; ?>> 1
					</label>
					<label>
						<input type="radio" name="binning" value="2"<?php echo (isset($config['ccd']['binning']) and ($config['ccd']['binning'] === 2)) ? ' checked' : ''; ?>> 2
					</label>
				</div>
			</div>

			<div class="form-group">
				<label>Разрядность (битность):</label>
				<div>
					<label>
						<input type="radio" name="bits" value="8"<?php echo (!isset($config['ccd']['bits']) or (isset($config['ccd']['bits']) and ($config['ccd']['bits'] === 8))) ? ' checked' : ''; ?>> 8
					</label>
					<label>
						<input type="radio" name="bits" value="16"<?php echo (isset($config['ccd']['bits']) and ($config['ccd']['bits'] === 16)) ? ' checked' : ''; ?>> 16
					</label>
				</div>
			</div>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Среднее значение яркости кадра</h6>
					<div class="form-group">
						<label>Минимум среднего ADU:</label>
						<input class="form-control" type="number" min="1" name="avgMin" value="<?php echo $config['ccd']['avgMin'] ?? '55'; ?>">
					</div>
					<div class="form-group">
						<label>Максимум среднего ADU:</label>
						<input class="form-control" type="number" min="1" max="65535" name="avgMax" value="<?php echo $config['ccd']['avgMax'] ?? '150'; ?>">
					</div>
					<div class="form-group">
						<label>Размер прямоугольника замера, в % от всего кадра:</label>
						<input class="form-control" type="number" min="1" max="100" name="center" value="<?php echo $config['ccd']['center'] ?? '50'; ?>">
					</div>
				</div>
			</div>

			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Подбор выдержки</h6>
					<div class="form-group">
						<label>Минимальная выдержка, секунд:</label>
						<input class="form-control" type="text" name="expMin" value="<?php echo $config['ccd']['expMin'] ?? '0.001'; ?>">
					</div>
					<div class="form-group">
						<label>Максимальная выдержка, секунд:</label>
						<input class="form-control" type="text" name="expMax" value="<?php echo $config['ccd']['expMax'] ?? '45'; ?>">
					</div>
					<div class="form-group">
						<label>Минимальный gain:</label>
						<input class="form-control" type="number" min="1" max="100" name="gainMin" value="<?php echo $config['ccd']['gainMin'] ?? '1'; ?>">
					</div>
					<div class="form-group">
						<label>Максимальный gain:</label>
						<input class="form-control" type="number" min="1" max="100" name="gainMax" value="<?php echo $config['ccd']['gainMax'] ?? '100'; ?>">
					</div>
					<div class="form-group">
						<label>Шаг подбора gain:</label>
						<input class="form-control" type="number" min="1" max="100" name="gainStep" value="<?php echo $config['ccd']['gainStep'] ?? '10'; ?>">
					</div>
				</div>
			</div>

			<br>
			<div>TBD: CFA</div>
			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>
	</div>

	<div class="tab-pane fade<?php echo $tab === 'processing' ? ' show active' : ''; ?>" id="processing">
		<br>
		<h5 class="card-title">Настройки обработки</h5>

		<form method="POST" class="processing" enctype="multipart/form-data">

			<input type="hidden" name="action" value="settings-processing">

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Обрезка (кроп)</h6>

					<div class="form-group">
						<label>Слева, пикселей:</label>
						<input class="form-control" type="number" name="left" value="<?php echo $config['processing']['crop']['left'] ?? '0'; ?>">
					</div>
					<div class="form-group">
						<label>Справа, пикселей:</label>
						<input class="form-control" type="number" name="right" value="<?php echo $config['processing']['crop']['right'] ?? '0'; ?>">
					</div>
					<div class="form-group">
						<label>Сверху, пикселей:</label>
						<input class="form-control" type="number" name="top" value="<?php echo $config['processing']['crop']['top'] ?? '0'; ?>">
					</div>
					<div class="form-group">
						<label>Снизу, пикселей:</label>
						<input class="form-control" type="number" name="bottom" value="<?php echo $config['processing']['crop']['bottom'] ?? '0'; ?>">
					</div>
				</div>
			</div>
			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Поворот / зеркало</h6>
					<div class="form-group">
						<div><label>Как есть:</label></div>
						<label>
							<input class="" type="radio" name="transpose" value="-1"
							<?php echo (!isset($config['processing']['transpose']) or $config['processing']['transpose'] == -1) ? 'checked' : ''; ?>> Без изменений<br>
						</label>
					</div>
					<div class="form-group">
						<div><label>Поворот:</label></div>
						<label>
							<input class="" type="radio" name="transpose" value="2"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 2) ? 'checked' : ''; ?>> Направо 90°
						</label>
						<br>
						<label>
							<input class="" type="radio" name="transpose" value="4"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 4) ? 'checked' : ''; ?>> Налево 90°
						</label>
						<br>
						<label>
							<input class="" type="radio" name="transpose" value="3"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 3) ? 'checked' : ''; ?>> На 180°<br>
						</label>
					</div>
					<div class="form-group">
						<div><label>Зеркалирование:</label></div>
						<label>
							<input class="" type="radio" name="transpose" value="0"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 0) ? 'checked' : ''; ?>> По горизонтали
						</label>
						<br>
						<label>
							<input class="" type="radio" name="transpose" value="1"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 1) ? 'checked' : ''; ?>> По вертикали
						</label>
						<br>
						<label>
							<input class="" type="radio" name="transpose" value="5"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 5) ? 'checked' : ''; ?>> По диагонали слева-сверху направо-вниз
						</label>
						<br>
						<label>
							<input class="" type="radio" name="transpose" value="6"
							<?php echo (isset($config['processing']['transpose']) and $config['processing']['transpose'] == 6) ? 'checked' : ''; ?>> По диагонали сверху-справа налево-вниз
						</label>
					</div>
				</div>
			</div>
			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Лого (наложение изображения)</h6>

					<div class="row">
						<div class="col-6">
							<div class="form-group">
								<label>Файл (jpg или png):</label>
								<input class="form-control" type="file" name="file">
							</div>
							<div class="form-group">
								<label>Координата Х наложения изображения:</label>
								<input class="form-control" type="number" min="0" name="logoX" value="<?php echo $config['processing']['logo']['x'] ?? 0; ?>">
							</div>
							<div class="form-group">
								<label>Координата Y наложения изображения:</label>
								<input class="form-control" type="number" min="0" name="logoY" value="<?php echo $config['processing']['logo']['y'] ?? 0; ?>">
							</div>
						</div>
						<div class="col-6">
							<?php if ($config['processing']['logo']['file'] ?? ''): ?>
								<img src="/<?php echo $config['processing']['logo']['file']; ?>" style="width: 300px" alt="Logo">
							<?php endif; ?>
						</div>
					</div>
				</div>
			</div>
			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Аннотации (наложение текста)</h6>

					<table class="table table-striped annotation">
						<thead>
						<tr>
							<th>Тип</th>
							<th>X</th>
							<th>Y</th>
							<th>Размер</th>
							<th>Цвет</th>
							<th>Формат</th>
							<th></th>
						</tr>
						</thead>
						<tbody>
						<?php if (count($config['processing']['annotation'] ?? []) > 0): ?>
							<?php foreach ($config['processing']['annotation'] as $annotation): ?>
								<tr>
									<td><?php echo $annotation['type']; ?></td>
									<td><?php echo $annotation['x']; ?></td>
									<td><?php echo $annotation['y']; ?></td>
									<td><?php echo $annotation['size']; ?></td>
									<td><?php echo $annotation['color']; ?></td>
									<td><?php echo $annotation['format']; ?></td>
									<td><button type="button" class="btn btn-danger btn-sm">&nbsp;-&nbsp;</button></td>
								</tr>
							<?php endforeach; ?>
						<?php else: ?>
							<tr class="empty">
								<td colspan="7" class="text-center">пусто</td>
							</tr>
						<?php endif; ?>
						</tbody>
					</table>

					<button class="btn btn-sm btn-info annotation-add">+</button>
				</div>

				<div class="modal annotation" tabindex="-1" role="dialog">
					<div class="modal-dialog" role="document">
						<div class="modal-content">
							<div class="modal-header">
								<h5 class="modal-title"></h5>
								<button type="button" class="close" data-dismiss="modal" aria-label="Close">
									<span aria-hidden="true">&times;</span>
								</button>
							</div>
							<div class="modal-body">
								<div class="form-group">
									<label>Тип аннотации</label>
									<select class="form-control" name="type">
										<option value="text">Текст</option>
										<option value="datetime">Дата / время</option>
										<option value="avg">Среднее ADU</option>
										<option value="exposure">Выдержка, сек</option>
										<option value="stars">Количество звёзд</option>
									</select>
								</div>
								<div class="form-group">
									<label>X координата</label>
									<input class="form-control" type="number" min="0" name="x">
								</div>
								<div class="form-group">
									<label>Y координата</label>
									<input class="form-control" type="number" min="0" name="y">
								</div>
								<div class="form-group">
									<label>Размер шрифта</label>
									<input class="form-control" type="number" min="3" max="100" name="size">
								</div>
								<div class="form-group">
									<label>Цвет</label>
									<div id="color" class="input-group">
										<input type="text" class="form-control input-lg" name="color">
										<span class="input-group-append">
											<span class="input-group-text colorpicker-input-addon"><i></i></span>
										</span>
									</div>
								</div>
								<div class="form-group">
									<label>Формат / текст</label>
									<input class="form-control" type="text" name="format">
								</div>
							</div>
							<div class="modal-footer">
								<button type="button" class="btn btn-primary"></button>
								<button type="button" class="btn btn-secondary" data-dismiss="modal">Закрыть</button>
							</div>
						</div>
					</div>
				</div>

				<script>
					function annotation_remove_event()
					{
						$('table.annotation tbody button.btn-danger').unbind('click');
						$('table.annotation tbody button.btn-danger').click(function (){
							if (confirm('Удалить аннотацию?')) {
								$(this).parents('tr').remove();

								if ($('table.annotation tbody tr').length == 1) {
									$('table.annotation tbody tr.empty').show();
								}
							}
						});
					}

					$(function (){
						$('#color').colorpicker({
							format: 'rgb',
							useAlpha: false
						});

						annotation_remove_event();

						$('.annotation .modal-footer button.btn-primary').click(function (){
							var message = '';

							if ($('.modal.annotation input[name=x]').val() == '') {
								message += 'Введите X координату<br>';
							}
							if ($('.modal.annotation input[name=y]').val() == '') {
								message += 'Введите Y координату<br>';
							}
							if ($('.modal.annotation input[name=size]').val() == '') {
								message += 'Введите размер шрифта<br>';
							}
							var color = $('.modal.annotation input[name=color]').val();
							if (color == '') {
								message += 'Выберите цвет<br>';
							}
							if (/^rgb(\d+, \d+, \d+)$/.test(color)) {
								message += 'Неверный формат кода цвета<br>';
							}
							if ($('.modal.annotation input[name=format]').val() == '') {
								message += 'Заполните формат / текст<br>';
							}

							if (message == '') {
								$('table.annotation tbody tr.empty').hide();

								$('table.annotation tbody').append('<tr>' +
									'<td>'+ $('.modal.annotation select[name=type]').val() +'</td>'+
									'<td>'+ $('.modal.annotation input[name=x]').val() +'</td>'+
									'<td>'+ $('.modal.annotation input[name=y]').val() +'</td>'+
									'<td>'+ $('.modal.annotation input[name=size]').val() +'</td>'+
									'<td>'+ $('.modal.annotation input[name=color]').val() +'</td>'+
									'<td>'+ $('.modal.annotation input[name=format]').val() +'</td>'+
									'<td><button type="button" class="btn btn-danger btn-sm">&nbsp;-&nbsp;</button></td>'+
									'</tr>');

								annotation_remove_event();

								$('.modal.annotation').modal('hide');
							}
							else {
								$.notify(
									{message: message},
									{
									   type: 'danger',
										z_index: 2000,
									}
								);
							}
						});

						$('.annotation-add').click(function (e){
							$('.annotation .modal-title').text('Добавление аннотации');
							$('.annotation .modal-footer button.btn-primary').text('Добавить');

							$('.modal.annotation select[name=type]').val('text');
							$('.modal.annotation input[name=x]').val('');
							$('.modal.annotation input[name=y]').val('');
							$('.modal.annotation input[name=size]').val('');
							$('.modal.annotation input[name=color]').val('');
							$('.modal.annotation input[name=format]').val('');

							$('.modal.annotation').modal();

							e.preventDefault();
						});
					});
				</script>
			</div>
			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Подсчёт количества звёзд</h6>

					<div class="form-group">
						<div>
							<label><input id="sd-enable" type="checkbox" name="sd[enable]"<?php echo (isset($config['processing']['sd']['enable']) and $config['processing']['sd']['enable']) ? ' checked' : ''; ?>> Подсчёт звёзд включён</label>
						</div>

						<div class="form-group sd-enable">
							<label>FWHM:</label>
							<input class="form-control" type="text" name="sd[fwhm]" value="<?php echo $config['processing']['sd']['fwhm'] ?? '1.5'; ?>">
						</div>
						<div class="form-group sd-enable">
							<label>Уровень (кратно STD):</label>
							<input class="form-control" type="text" name="sd[threshold]" value="<?php echo $config['processing']['sd']['threshold'] ?? '2'; ?>">
						</div>
					</div>
				</div>
				<script>
					$(function(){
						$('input#sd-enable').click(sd_enable);
					});

					sd_enable();
					function sd_enable()
					{
						if ($('input#sd-enable').is(':checked')) {
							$('.sd-enable').show();
						}
						else {
							$('.sd-enable').hide();
						}
					}
				</script>
			</div>

			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">Баланс белого (для цветных камер)</h6>

					<div class="form-group">
						<div>
							<label>Метод нахождения баланса белого:</label>
						</div>

						<div class="wb">
							<label>
								<input type="radio" name="wb" value="gain"<?php echo (!isset($config['processing']['wb']['type']) or (isset($config['processing']['wb']['type']) and ($config['processing']['wb']['type'] === 'gain'))) ? ' checked' : ''; ?>> Вручную
							</label>
							<label>
								<input type="radio" name="wb" value="simple"<?php echo (isset($config['processing']['wb']['type']) and ($config['processing']['wb']['type'] === 'simple')) ? ' checked' : ''; ?>> Simple WB
							</label>
							<label>
								<input type="radio" name="wb" value="gray"<?php echo (isset($config['processing']['wb']['type']) and ($config['processing']['wb']['type'] === 'gray')) ? ' checked' : ''; ?>> Greyworld WB
							</label>
						</div>
					</div>

					<div class="form-group" id="wb-gain" style="display: none">
						<div class="card">
							<div class="card-body">
								<h6 class="card-title">Gain-коэффициенты</h6>
								<div class="form-group">
									<label>Красный (R):</label>
									<input class="form-control" type="text" name="r" value="<?php echo $config['processing']['wb']['r'] ?? '1'; ?>">
								</div>
								<div class="form-group">
									<label>Зелёный (G):</label>
									<input class="form-control" type="text" name="g" value="<?php echo $config['processing']['wb']['g'] ?? '1'; ?>">
								</div>
								<div class="form-group">
									<label>Синий (B):</label>
									<input class="form-control" type="text" name="b" value="<?php echo $config['processing']['wb']['b'] ?? '1'; ?>">
								</div>
							</div>
						</div>
					</div>

					<script>
						function wb()
						{
							if ($('input[name=wb]:checked').val() == 'gain')
								$('#wb-gain').show();
							else
								$('#wb-gain').hide();
						}

						$(function (){
							wb();

							$('.wb input').click(wb);
						})
					</script>
				</div>
			</div>

			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>

			<script>
				$(function (){
					$('form.processing').submit(function (){
						var html = '';
						var i = 0;

						$('table.annotation tbody tr:not(.empty)').each(function (){
							html += '<input type="hidden" name="annotation['+ i +'][type]" value="'+ $(this).find('td:eq(0)').html() +'">';
							html += '<input type="hidden" name="annotation['+ i +'][x]" value="'+ $(this).find('td:eq(1)').html() +'">';
							html += '<input type="hidden" name="annotation['+ i +'][y]" value="'+ $(this).find('td:eq(2)').html() +'">';
							html += '<input type="hidden" name="annotation['+ i +'][size]" value="'+ $(this).find('td:eq(3)').html() +'">';
							html += '<input type="hidden" name="annotation['+ i +'][color]" value="'+ $(this).find('td:eq(4)').html() +'">';
							html += '<input type="hidden" name="annotation['+ i +'][format]" value="'+ $(this).find('td:eq(5)').html() +'">';

							i++;
						});

						$('form.processing').append(html);
					});
				});
			</script>

		</form>
	</div>

	<div class="tab-pane fade<?php echo $tab === 'publish' ? ' show active' : ''; ?>" id="publish">
		<br>
		<h5 class="card-title">Настройки публикации</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-publish">

			<div class="form-group">
				<label>URL для публикации JPG:</label>
				<input class="form-control" type="text" name="jpg" value="<?php echo $config['publish']['jpg'] ?? ''; ?>">
			</div>

			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>
	</div>

	<div class="tab-pane fade<?php echo $tab === 'sensors' ? ' show active' : ''; ?>" id="sensors">
		<br>
		<h5 class="card-title">Настройки дачтиков</h5>

		<form method="POST">

			<input type="hidden" name="action" value="settings-sensors">

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">BME280 (температура, влажность, давление)</h6>
					<div class="form-group">
						<label>Название первого датчика:</label>
						<input class="form-control" type="text" name="bme280[0][name]" value="<?php echo $config['sensors']['bme280'][0]['name'] ?? ''; ?>">
					</div>
					<div class="form-group">
						<label>Название второго датчика:</label>
						<input class="form-control" type="text" name="bme280[1][name]" value="<?php echo $config['sensors']['bme280'][1]['name'] ?? ''; ?>">
					</div>
				</div>
			</div>
			<br>

			<div class="card">
				<div class="card-body">
					<h6 class="card-title">ADS1115 (АЦП, датчик напряжения)</h6>
					<div class="form-group">
						<label>Название первого датчика:</label>
						<input class="form-control" type="text" name="ads1115[0][name]" value="<?php echo $config['sensors']['ads1115'][0]['name'] ?? ''; ?>">
					</div>
					<div class="form-group">
						<label>Делитель первого датчика:</label>
						<input class="form-control" type="text" name="ads1115[0][divider]" value="<?php echo $config['sensors']['ads1115'][0]['divider'] ?? ''; ?>">
					</div>
					<hr>
					<div class="form-group">
						<label>Название второго датчика:</label>
						<input class="form-control" type="text" name="ads1115[1][name]" value="<?php echo $config['sensors']['ads1115'][1]['name'] ?? ''; ?>">
					</div>
					<div class="form-group">
						<label>Делитель второго датчика:</label>
						<input class="form-control" type="text" name="ads1115[1][divider]" value="<?php echo $config['sensors']['ads1115'][1]['divider'] ?? ''; ?>">
					</div>
				</div>
			</div>

			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>

	</div>

	<div class="tab-pane fade<?php echo $tab === 'relays' ? ' show active' : ''; ?>" id="relays">
		<br>
		<h5 class="card-title">Настройки реле</h5>

		<form method="POST" class="relays">
			<input type="hidden" name="action" value="settings-relay">

			<table class="table table-striped relay">
				<thead>
				<tr>
					<th>Название</th>
					<th>GPIO порт</th>
					<th>Обогрев</th>
					<th>Температура</th>
					<th></th>
				</tr>
				</thead>
				<tbody>
					<?php if (count($config['relays'] ?? []) > 0): ?>
						<?php foreach ($config['relays'] as $relay): ?>
							<tr>
								<td><?php echo $relay['name']; ?></td>
								<td><?php echo $relay['gpio']; ?></td>
								<td><?php echo $relay['hotter'] ? 'обогрев' : ''; ?></td>
								<td><?php echo $relay['temp']; ?></td>
								<td><button type="button" class="btn btn-danger btn-sm">&nbsp;-&nbsp;</button></td>
							</tr>
						<?php endforeach; ?>
					<?php else: ?>
						<tr class="empty">
							<td colspan="5" class="text-center">пусто</td>
						</tr>
					<?php endif; ?>
				</tbody>
			</table>

			<button class="btn btn-sm btn-info relay-add">+</button>

			<div class="modal relay" tabindex="-1" role="dialog">
				<div class="modal-dialog" role="document">
					<div class="modal-content">
						<div class="modal-header">
							<h5 class="modal-title"></h5>
							<button type="button" class="close" data-dismiss="modal" aria-label="Close">
								<span aria-hidden="true">&times;</span>
							</button>
						</div>
						<div class="modal-body">
							<div class="form-group">
								<label>Название реле</label>
								<input class="form-control" type="text" name="name">
							</div>
							<div class="form-group">
								<label>GPIO порт</label>
								<input class="form-control" type="number" min="1" name="gpio">
							</div>
							<div class="form-group">
								<label>
									<input type="checkbox" name="hotter">
									Обогрев подкупольного
								</label>
							</div>
							<div class="form-group">
								<label>Желаемая температура обогрева</label>
								<input class="form-control" type="text" name="temp">
							</div>
						</div>
						<div class="modal-footer">
							<button type="button" class="btn btn-primary"></button>
							<button type="button" class="btn btn-secondary" data-dismiss="modal">Закрыть</button>
						</div>
					</div>
				</div>
			</div>

			<script>
				function relay_remove_event()
				{
					$('table.relay tbody button.btn-danger').unbind('click');
					$('table.relay tbody button.btn-danger').click(function (){
						if (confirm('Удалить реле?')) {
							$(this).parents('tr').remove();

							if ($('table.relay tbody tr').length == 1) {
								$('table.relay tbody tr.empty').show();
							}
						}
					});
				}

				$(function (){
					relay_remove_event();

					$('.relay .modal-footer button.btn-primary').click(function (){
						var message = '';

						if ($('.modal.relay input[name=name]').val() == '') {
							message += 'Введите название реле<br>';
						}
						if ($('.modal.relay input[name=gpio]').val() == '') {
							message += 'Выберите GPIO порт<br>';
						}

						if (message == '') {
							$('table.relay tbody tr.empty').hide();

							$('table.relay tbody').append('<tr>' +
								'<td>'+ $('.modal.relay input[name=name]').val() +'</td>'+
								'<td>'+ $('.modal.relay input[name=gpio]').val() +'</td>'+
								'<td>'+ (($('.modal.relay input[name=hotter]:checked').length == 1) ? 'обогрев' : '') +'</td>'+
								'<td>'+ $('.modal.relay input[name=temp]').val() +'</td>'+
								'<td><button type="button" class="btn btn-danger btn-sm">&nbsp;-&nbsp;</button></td>'+
								'</tr>');

							relay_remove_event();

							$('.modal.relay').modal('hide');
						}
						else {
							$.notify(
								{message: message},
								{
									type: 'danger',
									z_index: 2000,
								}
							);
						}
					});

					$('.relay-add').click(function (e){
						$('.relay .modal-title').text('Добавление реле');
						$('.relay .modal-footer button.btn-primary').text('Добавить');

						$('.modal.relay input[name=name]').val('');
						$('.modal.relay input[name=gpio]').val('');
						$('.modal.relay input[name=hotter]').prop('checked', false)
						$('.modal.relay input[name=temp]').val('');

						$('.modal.relay').modal();

						e.preventDefault();
					});
				});
			</script>
			<br>
			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>

			<script>
				$(function (){
					$('form.relays').submit(function (){
						var html = '';
						var i = 0;

						$('table.relay tbody tr:not(.empty)').each(function (){
							html += '<input type="hidden" name="relays['+ i +'][name]" value="'+ $(this).find('td:eq(0)').html() +'">';
							html += '<input type="hidden" name="relays['+ i +'][gpio]" value="'+ $(this).find('td:eq(1)').html() +'">';
							html += '<input type="hidden" name="relays['+ i +'][hotter]" value="'+ $(this).find('td:eq(2)').html() +'">';
							html += '<input type="hidden" name="relays['+ i +'][temp]" value="'+ $(this).find('td:eq(3)').html() +'">';

							i++;
						});

						$('form.relays').append(html);
					});
				});
			</script>
		</form>
	</div>

	<div class="tab-pane fade<?php echo $tab === 'archive' ? ' show active' : ''; ?>" id="archive">
		<br>
		<h5 class="card-title">Настройки архива</h5>

		<form method="POST">
			<input type="hidden" name="action" value="settings-archive">

			<div class="form-group">
				<label>Архив JPG, дней:</label>
				<input class="form-control" type="number" name="jpg" min="0" value="<?php echo $config['archive']['jpg'] ?? '7'; ?>">
			</div>

			<div class="form-group">
				<label>Архив FIT, дней:</label>
				<input class="form-control" type="number" name="fit" min="0" value="<?php echo $config['archive']['fit'] ?? '3'; ?>">
			</div>

			<div class="form-group">
				<label>Архив данных сенсоров, дней:</label>
				<input class="form-control" type="number" name="sensors" min="0" value="<?php echo $config['archive']['sensors'] ?? '30'; ?>">
			</div>

			<div class="form-group">
				<label>Архив видео (MP4), дней:</label>
				<input class="form-control" type="number" name="mp4" min="0" value="<?php echo $config['archive']['mp4'] ?? '30'; ?>">
			</div>

			<br>

			<button class="btn btn-success btn-lg" type="submit">Сохранить</button>
		</form>

	</div>
</div>

<?php include 'include/tail.php'; ?>
