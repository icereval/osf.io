<%inherit file="base.mako"/>
<%def name="title()">Project Statistics</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>
    <%
        if node.get('piwik_credentials'):
            piwik_url = '{host}index.php?module=Widgetize&action=iframe&moduleToWidgetize=Dashboard&actionToWidgetize=index&idSite={site_id}&period=day&date=today&disableLink=1&token_auth={auth_token}'.format(
                host=piwik_host,
                auth_token=node['piwik_credentials']['auth_token'],
                site_id=node['piwik_credentials']['site_id'],
            )
    %>
    % if not node.get('piwik_credentials'):
            <div class='alert alert-danger'><strong>Note:</strong> Statistics are available only for public resources.</div>
    % else:
        % if not node.get('is_public'):
            <div class='alert alert-warning'><strong>Note:</strong> Data are no longer being collected for this report, as this resource is private.</div>
        % endif
        <iframe style="overflow-y:scroll;border:none;" width="100%" height='600' src="${ piwik_url }"></iframe>
    % endif


</%def>
