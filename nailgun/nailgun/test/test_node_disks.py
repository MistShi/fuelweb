# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from nailgun.test.base import BaseHandlers, reverse
from nailgun.volumes.manager import DisksFormatConvertor


class TestNodeDisksHandlers(BaseHandlers):

    def create_node(self, role='controller'):
        self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[{
                'role': role,
                'pending_addition': True,
                'api': True}])

        return self.env.nodes[0]

    def get(self, node_id):
        resp = self.app.get(
            reverse('NodeDisksHandler', kwargs={'node_id': node_id}),
            headers=self.default_headers)

        self.assertEquals(200, resp.status)
        return json.loads(resp.body)

    def put(self, node_id, data):
        resp = self.app.put(
            reverse('NodeDisksHandler', kwargs={'node_id': node_id}),
            json.dumps(data),
            headers=self.default_headers)

        self.assertEquals(200, resp.status)
        return json.loads(resp.body)

    def test_default_attrs_after_creation(self):
        node = self.env.create_node(api=True)
        node_db = self.env.nodes[0]
        disks = self.get(node_db.id)

        self.assertGreater(len(disks), 0)
        for disk in disks:
            self.assertTrue(type(disk['size']) == int)
            self.assertGreaterEqual(disk['size'], 0)
            self.assertEqual(len(disk['volumes']), 0)

    def test_disks_recreation_after_node_agent_request(self):
        node = self.env.create_node(api=True)
        node_db = self.env.nodes[0]
        response = self.put(node_db.id, [])
        self.assertEquals(response, [])

        response = self.get(node_db.id)
        self.assertEquals(response, [])

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{"mac": node_db.mac, "is_agent": True}]),
            headers=self.default_headers)
        self.assertEquals(200, resp.status)

        response = self.get(node_db.id)
        self.assertNotEquals(response, [])

    def test_disks_volumes_size_update(self):
        node_db = self.create_node()
        disks = self.get(node_db.id)
        for disk in disks:
            for volume in disk['volumes']:
                volume['size'] = 4200

        response = self.put(node_db.id, disks)
        self.assertEquals(response, disks)

        response = self.get(node_db.id)
        self.assertEquals(response, disks)


class TestNodeDefaultsDisksHandler(BaseHandlers):

    def get(self, node_id):
        resp = self.app.get(
            reverse('NodeDefaultsDisksHandler', kwargs={'node_id': node_id}),
            headers=self.default_headers)

        self.assertEquals(200, resp.status)
        return json.loads(resp.body)

    def test_node_disk_amount_regenerates_volumes_info_if_new_disk_added(self):
        cluster = self.env.create_cluster(api=False)
        node = self.env.create_node(
            api=True,
            role='compute',  # vgs: os, vm
            cluster_id=cluster.id)
        node_db = self.env.nodes[0]
        response = self.get(node_db.id)
        self.assertEquals(len(response), 6)

        new_meta = node_db.meta.copy()
        new_meta['disks'].append({
            'size': 1000022933376,
            'model': 'SAMSUNG B00B135',
            'name': 'sda',
            'disk': 'disk/id/b00b135'})

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{
                "mac": node_db.mac,
                "meta": new_meta,
                "is_agent": True}]),
            headers=self.default_headers)

        self.env.refresh_nodes()

        response = self.get(node_db.id)
        self.assertEquals(len(response), 7)

        # check all groups on all disks
        vgs = ['os', 'vm']
        for disk in response:
            check_vgs = filter(
                lambda v: v['name'] in vgs,
                disk['volumes'])

            self.assertEquals(len(disk['volumes']), len(vgs))

    def test_get_default_attrs(self):
        node = self.env.create_node(api=True)
        node_db = self.env.nodes[0]
        volumes_from_api = self.get(node_db.id)

        default_volumes = node_db.volume_manager.gen_volumes_info()
        disks = filter(
            lambda volume: volume['type'] == 'disk', default_volumes)

        self.assertEquals(len(disks), len(volumes_from_api))


class TestNodeVolumesInformationHandler(BaseHandlers):

    def get(self, node_id):
        resp = self.app.get(
            reverse('NodeVolumesInformationHandler',
                    kwargs={'node_id': node_id}),
            headers=self.default_headers)

        self.assertEquals(200, resp.status)
        return json.loads(resp.body)

    def create_node(self, role):
        self.env.create(
            nodes_kwargs=[{'role': role, 'pending_addition': True}])

        return self.env.nodes[0]

    def check_volumes(self, volumes, volumes_ids):
        self.assertEquals(len(volumes), len(volumes_ids))
        for volume_id in volumes_ids:
            # Volume has name
            volume = filter(
                lambda volume: volume['name'] == volume_id, volumes)[0]
            # min_size
            self.assertTrue(type(volume['min_size']) == int)
            self.assertGreaterEqual(volume['min_size'], 0)
            # and label
            self.assertTrue(type(volume['label']) in (str, unicode))
            self.assertGreater(volume['label'], 0)

    def test_volumes_information_for_cinder_role(self):
        node_db = self.create_node('cinder')
        response = self.get(node_db.id)
        self.check_volumes(response, ['os', 'cinder'])

    def test_volumes_information_for_compute_role(self):
        node_db = self.create_node('compute')
        response = self.get(node_db.id)
        self.check_volumes(response, ['os', 'vm'])

    def test_volumes_information_for_controller_role(self):
        node_db = self.create_node('controller')
        response = self.get(node_db.id)
        self.check_volumes(response, ['os'])


class TestVolumeManager(BaseHandlers):

    def create_node(self, role):
        self.env.create(
            cluster_kwargs={},
            nodes_kwargs=[{
                'role': role,
                'pending_addition': True,
                'api': True}])

        return self.env.nodes[0]

    def non_zero_size(self, size):
        self.assertTrue(type(size) == int)
        self.assertGreater(size, 0)

    def os_size(self, disks):
        os_sum_size = 0
        for disk in self.only_disks(disks):
            os_volume = filter(
                lambda volume: volume.get('vg') == 'os', disk['volumes'])[0]

            os_sum_size += os_volume['size']

        self.non_zero_size(os_sum_size)
        return os_sum_size

    def reserved_size(self, spaces):
        reserved_size = 0
        for disk in self.only_disks(spaces):
            reserved_size += DisksFormatConvertor.\
                calculate_service_partitions_size(disk['volumes'])

        return reserved_size

    def filter_spaces_by_type(self, spaces, type):
        return filter(lambda space: space['type'] == type, spaces)

    def only_disks(self, spaces):
        return self.filter_spaces_by_type(spaces, 'disk')

    def only_vg(self, spaces):
        return self.filter_spaces_by_type(spaces, 'vg')

    def should_contain_os_with_minimal_size(self, volume_manager):
        self.assertEquals(
            self.os_size(volume_manager.volumes),
            volume_manager.call_generator('calc_min_os_size'))

    def all_free_space_except_os_for_volume(self, spaces, volume_name):
        os_size = self.os_size(spaces)
        reserved_size = self.reserved_size(spaces)
        vg_size = 0
        disk_sum_size = sum([disk['size'] for disk in self.only_disks(spaces)])
        for disk in self.only_disks(spaces):
            for volume in disk['volumes']:
                if volume.get('vg') == volume_name:
                    vg_size += volume['size']

        self.assertEquals(
            vg_size, disk_sum_size - os_size - reserved_size)

    def logical_volume_sizes_should_equal_all_phisical_volumes(self, spaces):
        vg_sizes = {}
        for vg in self.only_vg(spaces):
            for volume in vg['volumes']:
                vg_name = vg['id']
                if not vg_sizes.get(vg_name):
                    vg_sizes[vg_name] = 0
                vg_sizes[vg_name] += volume['size']

        pv_sizes = {}
        test = 0
        for disk in self.only_disks(spaces):
            for volume in disk['volumes']:
                if volume['type'] == 'pv':
                    vg_name = volume['vg']
                    if not pv_sizes.get(vg_name):
                        pv_sizes[vg_name] = 0

                    pv_sizes[vg_name] += volume['size']
                elif volume['type'] == 'lvm_meta':
                    vg_name = volume['name']
                    if not pv_sizes.get(vg_name):
                        pv_sizes[vg_name] = 0

                    pv_sizes[vg_name] -= volume['size']

        self.assertEquals(vg_sizes, pv_sizes)

    def check_disk_size_equal_sum_of_all_volumes(self, spaces):
        for disk in self.only_disks(spaces):
            volumes_size = sum(
                [volume.get('size', 0) for volume in disk['volumes']])

            self.assertEquals(volumes_size, disk['size'])

    def test_allocates_all_free_space_for_os_for_controller_role(self):
        node = self.create_node('controller')
        disks = self.only_disks(node.volume_manager.volumes)
        disks_size_sum = sum([disk['size'] for disk in disks])
        os_sum_size = self.os_size(disks)
        reserved_size = self.reserved_size(disks)

        self.assertEquals(disks_size_sum - reserved_size, os_sum_size)
        self.logical_volume_sizes_should_equal_all_phisical_volumes(
            node.attributes.volumes)
        self.check_disk_size_equal_sum_of_all_volumes(node.attributes.volumes)

    def test_allocates_all_free_space_for_vm_for_compute_role(self):
        node = self.create_node('compute')
        self.should_contain_os_with_minimal_size(node.volume_manager)
        self.all_free_space_except_os_for_volume(
            node.volume_manager.volumes, 'vm')
        self.logical_volume_sizes_should_equal_all_phisical_volumes(
            node.attributes.volumes)
        self.check_disk_size_equal_sum_of_all_volumes(node.attributes.volumes)

    def test_allocates_all_free_space_for_vm_for_cinder_role(self):
        node = self.create_node('cinder')
        self.should_contain_os_with_minimal_size(node.volume_manager)
        self.all_free_space_except_os_for_volume(
            node.volume_manager.volumes, 'cinder')
        self.check_disk_size_equal_sum_of_all_volumes(node.attributes.volumes)
