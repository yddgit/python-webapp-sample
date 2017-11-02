-- schema.sql
-- help:
--   Login MySQL: mysql -u root -p
--   Execute Script: source /path/to/schema.sql
drop database if exists test;
create database test;
use test;
create user if not exists 'www-data'@'localhost' identified by 'www-data';
-- grant select, insert, update, delete on test.* to 'www-data'@'localhost' identified by 'www-data';
grant all privileges on test.* to 'www-data'@'localhost' identified by 'www-data';
-- generating SQL for users:
create table `users` (
  `id` varchar(50) not null,
  `email` varchar(255) not null,
  `password` varchar(50) not null,
  `admin` bool not null,
  `name` varchar(50) not null,
  `image` varchar(500) not null,
  `created_at` real not null,
  primary key(`id`)
);
-- generating SQL for blogs:
create table `blogs` (
  `id` varchar(50) not null,
  `user_id` varchar(50) not null,
  `user_name` varchar(50) not null,
  `user_image` varchar(500) not null,
  `name` varchar(50) not null,
  `summary` varchar(200) not null,
  `content` text not null,
  `created_at` real not null,
  primary key(`id`)
);
-- generating SQL for comments:
create table `comments` (
  `id` varchar(50) not null,
  `blog_id` varchar(50) not null,
  `user_id` varchar(50) not null,
  `user_name` varchar(50) not null,
  `user_image` varchar(500) not null,
  `content` text not null,
  `created_at` real not null,
  primary key(`id`)
);