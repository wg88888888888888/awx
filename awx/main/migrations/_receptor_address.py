import logging
from django.db import DatabaseError, transaction


logger = logging.getLogger('awx.main.migrations')


def _emulate_receptor_address_save_signal(address, Instance):
    # TODO: cmeyers. I'm thinking we can delete this method. I don't call it.
    # However, need to check with Seth.
    # My assumption is that this logic has already ran _before_ this feature so
    # InstanceLink that is created here should already exist.
    control_instances = set(Instance.objects.filter(node_type__in=['control', 'hybrid']))
    if address.peers_from_control_nodes:
        if set(address.peers_from.all()) != control_instances:
            address.peers_from.add(*control_instances)
            return control_instances
    return None


def migrate_instance_relationship_to_receptor_relationships(apps, schema_editor):
    """
    The migration that calls this function creates an extra table that you won't find
    in the models, InstanceLinkReceptorAddress. This table will become the new InstanceLink.
    During this migration, the old table, InstanceLink, has the data that we migrate to
    InstanceLinkReceptorAddress. Drop InstanceLink, rename InstanceLinkReceptorAddress
    to InstanceLink.
    """
    Instance = apps.get_model('main', 'Instance')
    InstanceLink = apps.get_model('main', 'InstanceLink')
    ReceptorAddress = apps.get_model('main', 'ReceptorAddress')

    ReceptorAddress.objects.bulk_create(
        [
            ReceptorAddress(
                instance=inst, address=inst.ip_address or inst.hostname, port=inst.listener_port, peers_from_control_nodes=inst.peers_from_control_nodes
            )
            for inst in Instance.objects.exclude(listener_port=None)
        ]
    )

    # addr_map = {addr.instance.id: addr for addr in addrs}
    # TODO: cmeyers, should we also rewrite the receptor config(s) after the migration ???
    # _emulate_receptor_address_save_signal(raddr, Instance)

    for link in InstanceLink.objects.all():
        # link.source.peers.add(addr_map[link.target.id])
        link.source.peers.add(ReceptorAddress.objects.get(instance=link.target))
