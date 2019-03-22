create database allsky;
use allsky;

grant all privileges on allsky.* to root@localhost identified by 'master';

create table config (
	id varchar(100) not null primary key,
	val text not null
);

create table user (
	id int unsigned auto_increment not null primary key,
	email varchar(255) not null,
	name varchar(255) not null,
	password varchar(255) not null
);

insert into user (email, name, password) values ('admin', 'admin', 'admin');

create table sensor (
	id int unsigned auto_increment not null primary key,
	type enum('temperature', 'humidity', 'pressure', 'voltage', 'wind-speed', 'wind-direction', 'sky-temperature') not null,
	channel int unsigned not null,
	date int unsigned not null,
	val double not null
);
alter table sensor add index channel_type_date (channel, type, date);