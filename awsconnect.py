#!/usr/bin/python3

import socket
import sys
from subprocess import call

import boto3
import yaml
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


def get_instance_name(instance):
    return [t.get('Value') for t in instance.tags if t.get('Key', None) == 'Name'].pop()


def open_tab_and_connect_ssh(name, address, key):
    @pyqtSlot()
    def open_tab_and_connect_ssh_fn():
        print("Connecting to %s by address %s with key %s ..." % (name, address, key))
        call(['konsole',
              '--new-tab',
              '-p', 'RemoteTabTitleFormat=\"%s : (%s)\"' % (name, address),
              '-e', "/bin/bash -c \"ssh -i %s ubuntu@%s\"" % (key, address)])

    return open_tab_and_connect_ssh_fn


def copy_to_clipboard(address):
    @pyqtSlot()
    def copy_to_clipboard_fn():
        print("Address copied to clipboard")
        QApplication.clipboard().setText(address)

    return copy_to_clipboard_fn


def load_hosts(connections):
    loaded_instances = {}

    for connection in connections:
        ec2 = boto3.resource(
            'ec2',
            region_name=connection['region'],
            aws_access_key_id=connection['aws_access_key_id'],
            aws_secret_access_key=connection['aws_secret_access_key']
        )
        ec2_instances = ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        loaded_instances[connection['name']] = sorted(ec2_instances, key=lambda i: get_instance_name(i))

        print("[%s]" % connection['name'])
        for instance in loaded_instances[connection['name']]:
            name = get_instance_name(instance)
            print(instance.id, instance.instance_type, instance.public_dns_name, name)

    return loaded_instances


class AWSConnect(QDialog):
    def __init__(self, config=None, parent=None):
        QWidget.__init__(self, parent)

        self.keys = config['keys']

        self.instances = load_hosts(config['connections'])

        self.create_tray_icon()

    def create_tray_icon(self):
        self.tray_icon_menu = QMenu(self)

        for connection_name in self.instances:
            connection_menu = self.tray_icon_menu.addMenu(connection_name)

            for instance in self.instances[connection_name]:
                name = get_instance_name(instance)
                instance_menu = connection_menu.addMenu(name)
                instance_menu.addAction(self.create_action('Connect',
                                                           open_tab_and_connect_ssh(name,
                                                                                    instance.public_dns_name,
                                                                                    self.keys[instance.key_name])))
                instance_menu.addAction(self.create_action('Copy to clipboard',
                                                           copy_to_clipboard(instance.public_dns_name)))

        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(qApp.quit)
        self.tray_icon_menu.addAction(self.quit_action)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setContextMenu(self.tray_icon_menu)

        self.tray_icon.setIcon(QIcon("favicon.ico"))

        self.tray_icon.activated.connect(self.icon_activated)

        self.tray_icon.show()

    def create_action(self, action_name, action_function):
        action = QAction(action_name, self)
        action.triggered.connect(action_function)
        return action

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def icon_activated(self, reason):
        pass
        # if reason == 3:  # click
        #     self.show()
        # if reason == 2: # double click


def read_config(config_file_name):
    with open(config_file_name, 'r', encoding='utf-8') as f:
        return yaml.load(f)


if __name__ == "__main__":
    socket.setdefaulttimeout(60)

    if len(sys.argv) == 1:
        app_config = read_config("settings.yaml")
    else:
        app_config = read_config(sys.argv[1])

    app = QApplication(sys.argv)
    myapp = AWSConnect(app_config)
    sys.exit(app.exec_())
