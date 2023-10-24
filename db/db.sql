
create table allsky.config (
	id varchar(100) not null primary key,
	val text not null
--	user_id int unsigned not null,
--	date int unsigned not null
);

INSERT INTO `config` (`id`, `val`) VALUES ('archive','{\"jpg\":30,\"fit\":3,\"sensors\":30,\"mp4\":30}'),('ccd','{\"binning\":1,\"bits\":8,\"avgMin\":55,\"avgMax\":150,\"center\":50,\"expMin\":0.001,\"expMax\":45,\"gainMin\":1,\"gainMax\":100,\"gainStep\":11}'),('processing','{\"crop\":{\"left\":0,\"right\":0,\"top\":0,\"bottom\":0},\"logo\":{\"x\":0,\"y\":0},\"annotation\":null,\"wb\":{\"type\":\"gain\",\"r\":\"8\",\"g\":\"1.2\",\"b\":\"0.9\"}}'),('publish','{\"jpg\":\"https:\\/\\/allsky.milantiev.com\\/publish\\/jpg\"}'),('relays','[]'),('sensors','{\"bme280\":[{\"name\":\"\"},{\"name\":\"\"}],\"ads1115\":[{\"name\":\"\",\"divider\":\"\"},{\"name\":\"\",\"divider\":\"\"}]}'),('web','{\"name\":\"\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435\",\"counter\":\"\"}');

create table allsky.user (
	id int unsigned auto_increment not null primary key,
	email varchar(255) not null,
	name varchar(255) not null,
	password varchar(255) not null
);

insert into allsky.user (email, name, password) values ('admin', 'admin', 'admin');

create table allsky.sensor (
	id int unsigned auto_increment not null primary key,
	type enum('temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average', 'ccd-gain', 'ccd-bin', 'stars-count', 'ai-clear', 'ai-cloud') not null,
	channel int unsigned not null,
	date int unsigned not null,
	val double not null
);
alter table allsky.sensor add index channel_type_date (channel, type, date);
alter table allsky.sensor add index type (type);

create table allsky.sensor_last (
	type enum('temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average', 'ccd-gain', 'ccd-bin', 'stars-count', 'ai-clear', 'ai-cloud') not null,
	channel int unsigned not null,
	date int unsigned not null,
	val double not null,
	primary key (type, channel)
);

create table allsky.relay (
	id varchar(100) not null primary key,
	state tinyint(1) not null,
	date int unsigned not null
);

-- запросы на создание видео
create table allsky.video (
	id int unsigned auto_increment not null primary key,
	job varchar(100) not null,
	work_queue int unsigned not null,
	work_begin int unsigned not null,
	work_end int unsigned not null,
	video_begin int unsigned not null,
	video_end int unsigned not null,
	frames int unsigned not null
);
