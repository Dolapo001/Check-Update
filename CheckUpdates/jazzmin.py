JAZZMIN_SETTINGS = {
    "site_title": "Content Management System",
    "site_header": "Admin Portal",
    "site_brand": "CMS Admin",
    "site_logo": "logo.png",
    "login_logo": "logo.png",
    "site_logo_classes": "img-circle",
    "site_icon": "logo.png",
    "welcome_sign": "Welcome to the Content Management System",
    "copyright": " Ltd 2025",

    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:dashboard", "permissions": ["auth.view_user"]},
        {"name": "Site Home", "url": "/", "new_window": True},
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
    ],

    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": {
        "authtoken": ["tokenproxy"],
        "token_blacklist": ["blacklistedtoken", "outstandingtoken"],
    },
    "order_with_respect_to": ["auth", "cms"],

    "icons": {
        "auth.Group": "fas fa-users",
        "cms.Role": "fas fa-user-tag",
        "cms.AdminUser": "fas fa-user-shield",
        "cms.AdminActionLog": "fas fa-clipboard-list",
        "cms.Content": "fas fa-file-alt",
        "cms.AdBanner": "fas fa-ad",
        "cms.Comment": "fas fa-comments",
        "cms.SEOData": "fas fa-search",
        "core.group": "fas fa-users",
        "core.user": "fas fa-universal-access",
        "core.profile": "fas fa-user",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    "usermenu_links": [
        {"name": "Platform", "url": "/"},
        {"model": "auth.user"},
    ],

    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },

    "related_modal_active": True,
    "custom_css": "css/admin-custom.css",
    "user_avatar": "avatar",
}
