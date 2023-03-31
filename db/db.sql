
create table allsky.config (
	id varchar(100) not null primary key,
	val text not null
--	user_id int unsigned not null,
--	date int unsigned not null
);

create table allsky.user (
	id int unsigned auto_increment not null primary key,
	email varchar(255) not null,
	name varchar(255) not null,
	password varchar(255) not null
);

insert into allsky.user (email, name, password) values ('admin', 'admin', 'admin');

create table allsky.sensor (
	id int unsigned auto_increment not null primary key,
	type enum('temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average') not null,
	channel int unsigned not null,
	date int unsigned not null,
	val double not null
);
alter table allsky.sensor add index channel_type_date (channel, type, date);
alter table allsky.sensor add index type (type);

create table allsky.sensor_last (
	type enum('temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature', 'ccd-exposure', 'ccd-average') not null,
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
