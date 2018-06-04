# -*- coding:utf-8 -*-
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.db import models
from authority.models import ExtendUser
import uuid
import paramiko
import socket
from deveops.utils.msg import Message
from deveops.utils import sshkey,aes
from utils.models import FILE
from django.contrib.auth.models import Group as PerGroup
from authority.models import Key,Jumper

__all__ = [
    "System_Type", "Group", "Host",
    "Position", "HostDetail"
]


class System_Type(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, default="")
    class Meta:
        permissions = (('yo_list_systype', u'罗列系统类型'),
                       ('yo_create_systype', u'新增系统类型'),
                       ('yo_update_systype', u'修改系统类型'),
                       ('yo_detail_systype', u'详细系统类型'),
                       ('yo_delete_systype', u'删除系统类型'))

    def __unicode__(self):
        return self.name

    @property
    def sum_host(self):
        return self.hosts.count()


class Position(models.Model):
    id = models.AutoField(primary_key=True) #全局ID
    uuid = models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, default="") #字符长度

    class Meta:
        permissions = (('yo_list_position', u'罗列位置'),
                       ('yo_create_position', u'新增位置'),
                       ('yo_update_position', u'修改位置'),
                       ('yo_detail_position', u'详细位置'),
                       ('yo_delete_position', u'删除位置'))

    def __unicode__(self):
        return self.name


class Group(models.Model):
    GROUP_STATUS=(
        (0, '禁用中'),
        (1, '使用中'),
        (2, '暂停中'),
        (3, '不可达'),
    )
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100, default='')
    info = models.CharField(max_length=100, default='')
    _framework = models.ForeignKey(FILE, related_name='groups', on_delete=models.SET_NULL, null=True)
    # 超级管理员
    users = models.ManyToManyField(ExtendUser, blank=True, related_name='assetgroups', verbose_name=_("assetgroups"))
    _status = models.IntegerField(choices=GROUP_STATUS, default=0)
    pmn_groups = models.ManyToManyField(PerGroup, blank=True, related_name='assetgroups', verbose_name=_("assetgroups"))

    # 操作凭证
    key = models.OneToOneField(Key, related_name='group', on_delete=models.SET_NULL, null=True, blank=True)
    jumper = models.OneToOneField(Jumper, related_name='group', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        permissions = (('yo_list_group', u'罗列应用组'),
                       ('yo_create_group', u'新增应用组'),
                       ('yo_update_group', u'修改应用组'),
                       ('yo_detail_group', u'详细查看应用组'),
                       ('yo_delete_group', u'删除应用组'))

    def __unicode__(self):
        return self.name

    __str__ = __unicode__

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if status == 1:
            if self.key is not None and self.jumper is not None and self.jumper.status == 1:
                self._status = 1
            else:
                self._status = 3
        else:
            self._status = status

    def framework_update(self):
        if not self._framework is None:
            self._framework.delete()
        return True

    @property
    def framework(self):
        return self._framework.file

    @framework.setter
    def framework(self, framework):
        self._framework = framework

    @property
    def users_list_byconnectip(self):
        if self._status != 1:
            return []
        else:
            # Ansible 2.0.0.0
            # return list(self.hosts.values_list('connect_ip', flat=True)) Only Normal Host
            return ','.join(list(self.hosts.filter(_status=1).values_list('connect_ip', flat=True)))

    @property
    def group_vars(self):
        return self.vars.all()

    @property
    def users_list_byhostname(self):
        return list(self.hosts.values_list('hostname', flat=True))


class HostDetail(models.Model):
    id=models.AutoField(primary_key=True) #全局ID
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, related_name='hosts_detail')
    systemtype = models.ForeignKey(System_Type, on_delete=models.SET_NULL, null=True, related_name='hosts_detail')
    info = models.CharField(max_length=200, default="", null=True, blank=True)
    aliyun_id = models.CharField(max_length=30, default='', blank=True, null=True)
    vmware_id = models.CharField(max_length=36, default='', blank=True, null=True)


class Host(models.Model):
    SYSTEM_STATUS = (
        (0, '错误'),
        (1, '正常'),
        (2, '不可达'),
    )
    # 主机标识
    id = models.AutoField(primary_key=True) #全局ID
    uuid = models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False)
    # 资产结构
    groups = models.ManyToManyField(Group, blank=True, related_name='hosts', verbose_name=_("Host"))

    # 相关信息
    # connect_ip = models.GenericIPAddressField(default='', null=False)
    connect_ip = models.CharField(max_length=15, default='', null=False)
    service_ip = models.CharField(max_length=15, default='0.0.0.0', null=True)
    # service_ip = models.GenericIPAddressField(default='0.0.0.0', null=True)

    # 主机名称
    hostname = models.CharField(max_length=50, default='localhost.localdomain', null=True, blank=True)

    # 用户端口
    sshport = models.IntegerField(default='22')
    detail = models.ForeignKey(HostDetail, related_name='host', on_delete=models.SET_NULL, null=True)
    _passwd = models.CharField(max_length=1000, default='', null=True, blank=True)

    # 服务器状态
    _status = models.IntegerField(default=1, choices=SYSTEM_STATUS)

    class Meta:
        permissions = (
            ('yo_list_host', u'罗列主机'),
            ('yo_create_host', u'新增主机'),
            ('yo_update_host', u'修改主机'),
            ('yo_delete_host', u'删除主机'),
            ('yo_detail_host', u'详细查看主机'),
            ('yo_passwd_host', u'获取主机密码'),
            ('yo_webskt_host', u'远控主机')
        )

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self,status):
        self._status = status

    @property
    def password(self):
        if self._passwd:
            return aes.decrypt(self._passwd)
        else:
            return 'nopassword'

    @password.setter
    def password(self, password):
        self._passwd = aes.encrypt(password).decode()

    def manage_user_get(self):
        dist = {}
        for group in self.groups.all():
            for user in group.users.all():
                dist[user.email]=user
        list = []
        for key in dist:
            list.append(dist[key])
        return list
