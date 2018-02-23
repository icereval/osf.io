# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-22 20:39
from __future__ import unicode_literals

import gc
import logging
import progressbar
from django.db import migrations
from django.db.models import Q
from osf.utils.migrations import disable_auto_now_add_fields
from django.contrib.contenttypes.models import ContentType
from addons.wiki.models import WikiPage, NodeWikiPage, WikiVersion
from osf.models import Comment, Guid, AbstractNode
from bulk_update.helper import bulk_update
logger = logging.getLogger(__name__)

def reverse_func(state, schema):
    """
    Reverses NodeWikiPage migration. Repoints guids back to each NodeWikiPage,
    repoints comment_targets, comments_viewed_timestamps, and deletes all WikiVersions and WikiPages
    """
    nwp_content_type_id = ContentType.objects.get_for_model(NodeWikiPage).id

    nodes = AbstractNode.objects.exclude(wiki_pages_versions={})
    progress_bar = progressbar.ProgressBar(maxval=nodes.count()).start()
    for i, node in enumerate(nodes, 1):
        progress_bar.update(i)
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            if version_list:
                for index, version in enumerate(version_list):
                    nwp = NodeWikiPage.objects.get(former_guid=version)
                    wp = WikiPage.load(version)
                    guid = migrate_guid_referent(Guid.load(version), nwp, nwp_content_type_id)
                    guid.save()
                    nwp = guid.referent
                move_comment_target(Guid.load(wp._id), wp, nwp)
                update_comments_viewed_timestamp(node, wp, nwp)
    progress_bar.finish()
    WikiVersion.objects.all().delete()
    WikiPage.objects.all().delete()
    logger.info('NodeWikiPages restored and WikiVersions and WikiPages removed.')

def move_comment_target(current_guid, current_target, desired_target):
    """Move the comment's target from the current target to the desired target"""
    desired_target_guid = Guid.load(desired_target._id)
    if Comment.objects.filter(Q(root_target_id=current_guid) | Q(target=current_guid)).exists():
        Comment.objects.filter(root_target=current_guid).update(root_target=desired_target_guid)
        Comment.objects.filter(target=current_guid).update(target=desired_target_guid)
    return

def update_comments_viewed_timestamp(node, current_wiki_object, desired_wiki_object):
    """Replace the current_wiki_object keys in the comments_viewed_timestamp dict with the desired wiki_object_id """
    contributors_pending_save = []
    for contrib in node.contributors.exclude(comments_viewed_timestamp={}):
        if contrib.comments_viewed_timestamp.get(current_wiki_object._id, None):
            timestamp = contrib.comments_viewed_timestamp[current_wiki_object._id]
            contrib.comments_viewed_timestamp[desired_wiki_object._id] = timestamp
            del contrib.comments_viewed_timestamp[current_wiki_object._id]
            contributors_pending_save.append(contrib)
    bulk_update(contributors_pending_save, batch_size=1000)
    return

def migrate_guid_referent(guid, desired_referent, content_type_id):
    """
    Point the guid towards the desired_referent.
    Pointing the NodeWikiPage guid towards the WikiPage will still allow links to work.
    """
    guid.content_type_id = content_type_id
    guid.object_id = desired_referent.id
    return guid

def create_wiki_page(node, node_wiki, page_name):
    wp = WikiPage(
        page_name=page_name,
        user_id=node_wiki.user_id,
        node=node,
        created=node_wiki.date,
        modified=node_wiki.modified,
    )
    wp.update_modified = False
    return wp

def create_wiki_version(node_wiki, wiki_page):
    wv = WikiVersion(
        wiki_page=wiki_page,
        user_id=node_wiki.user_id,
        created=node_wiki.date,
        modified=node_wiki.modified,
        content=node_wiki.content,
        identifier=node_wiki.version,
    )
    wv.update_modified = False
    return wv

def create_guids():
    content_type = ContentType.objects.get_for_model(WikiPage)
    progress_bar = progressbar.ProgressBar(maxval=WikiPage.objects.count()).start()
    logger.info('Creating new guids for all WikiPages:')
    for i, wp in enumerate(WikiPage.objects.all(), 1):
        # looping instead of bulk_create, so _id's are not the same
        progress_bar.update(i)
        Guid.objects.create(object_id=wp.id, content_type_id=content_type.id)
    progress_bar.finish()
    logger.info('WikiPage guids created.')
    return

def create_wiki_pages(nodes):
    wiki_pages = []
    progress_bar = progressbar.ProgressBar(maxval=nodes.count()).start()
    logger.info('Starting migration of WikiPages:')
    for i, node in enumerate(nodes, 1):
        progress_bar.update(i)
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            if version_list:
                node_wiki = NodeWikiPage.objects.filter(former_guid=version_list[0]).only('user_id', 'date', 'modified').include(None).get()
                latest_page_name = NodeWikiPage.objects.filter(former_guid=version_list[-1]).values_list('page_name', flat=True).include(None).get()
                wiki_pages.append(create_wiki_page(node, node_wiki, latest_page_name))
        if i % 500 == 0:
            with disable_auto_now_add_fields(models=[WikiPage]):
                WikiPage.objects.bulk_create(wiki_pages, batch_size=1000)
                wiki_pages = []
    progress_bar.finish()
    # Create the remaining wiki pages that weren't created in the loop above
    with disable_auto_now_add_fields(models=[WikiPage]):
        WikiPage.objects.bulk_create(wiki_pages, batch_size=1000)
    logger.info('WikiPages saved.')
    create_guids()
    return

def create_wiki_versions(nodes):
    wp_content_type_id = ContentType.objects.get_for_model(WikiPage).id
    wiki_versions_pending = []
    guids_pending = []
    progress_bar = progressbar.ProgressBar(maxval=nodes.count()).start()
    logger.info('Starting migration of WikiVersions:')
    for i, node in enumerate(nodes, 1):
        progress_bar.update(i)
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            if version_list:
                node_wiki = NodeWikiPage.objects.get(former_guid=version_list[0])
                page_name = NodeWikiPage.objects.filter(former_guid=version_list[-1]).values_list('page_name', flat=True).include(None).get()
                wiki_page = node.wikis.get(page_name=page_name)
                for index, version in enumerate(version_list):
                    if index:
                        node_wiki = NodeWikiPage.objects.get(former_guid=version)
                    wiki_versions_pending.append(create_wiki_version(node_wiki, wiki_page))
                    current_guid = Guid.load(version)
                    guids_pending.append(migrate_guid_referent(current_guid, wiki_page, wp_content_type_id))
                move_comment_target(current_guid, node_wiki, wiki_page)
                update_comments_viewed_timestamp(node, node_wiki, wiki_page)
        if i % 500 == 0:
            with disable_auto_now_add_fields(models=[WikiVersion]):
                WikiVersion.objects.bulk_create(wiki_versions_pending, batch_size=1000)
                wiki_versions_pending = []
            bulk_update(guids_pending, batch_size=1000)
            guids_pending = []
            gc.collect()
    progress_bar.finish()
    # Create the remaining wiki pages that weren't created in the loop above
    with disable_auto_now_add_fields(models=[WikiVersion]):
        WikiVersion.objects.bulk_create(wiki_versions_pending, batch_size=1000)
    bulk_update(guids_pending, batch_size=1000)
    logger.info('WikiVersions saved.')
    logger.info('Repointed NodeWikiPage guids to corresponding WikiPage')
    return

def migrate_node_wiki_pages(state, schema):
    """
    For every node, loop through all the NodeWikiPages on node.wiki_pages_versions.  Create a WikiPage, and then a WikiVersion corresponding
    to each WikiPage.
        - Loads all nodes with wikis on them.
        - For each node, loops through all the keys in wiki_pages_versions.
        - Creates all wiki pages and then bulk creates them, for speed.
        - For all wiki pages that were just created, create and save a guid (since bulk_create doesn't call save method)
        - Loops through all nodes again, creating a WikiVersion for every guid for all wiki pages on a node.
        - Repoints guids from old wiki to new WikiPage
        - For the most recent version of the WikiPage, repoint comments to the new WikiPage
        - For comments_viewed_timestamp that point to the NodeWikiPage, repoint to the new WikiPage
    """
    nodes_with_wikis = AbstractNode.objects.exclude(wiki_pages_versions={})
    if nodes_with_wikis:
        create_wiki_pages(nodes_with_wikis)
        create_wiki_versions(nodes_with_wikis)
    return


class Migration(migrations.Migration):

    dependencies = [
        ('addons_wiki', '0008_store_guid_on_nodewikipage'),
    ]

    operations = [
        migrations.RunPython(migrate_node_wiki_pages, reverse_func)
    ]