JAZZMIN_SETTINGS = {
    "site_title": "Content Management System",
    "site_header": "CheckUpdate Admin Panel",
    "site_brand": "CheckUpdate Admin",
    "site_logo": "img/logo.jpg",
    "login_logo": "img/logo.jpg",
    "site_logo_classes": "img-circle",
    "site_icon": "img/logo.jpg",
    "welcome_sign": "Welcome to the Content Management System",
    "copyright": " Ltd 2025",

    # FIXED: Use correct admin URL names
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},  # Changed to admin:index
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

    # FIXED: Update icon references to use correct app labels
    "icons": {
        "auth.Group": "fas fa-users",
        "auth.User": "fas fa-user",  # Added for auth user
        "admin_roles.Role": "fas fa-user-tag",  # Fixed app label
        "admin_roles.AdminUser": "fas fa-user-shield",  # Fixed app label
        "admin_roles.AdminActionLog": "fas fa-clipboard-list",  # Fixed app label
        "admin_roles.Content": "fas fa-file-alt",  # Fixed app label
        "admin_roles.AdBanner": "fas fa-ad",  # Fixed app label
        "admin_roles.Comment": "fas fa-comments",  # Fixed app label
        "admin_roles.SEOData": "fas fa-search",  # Fixed app label
        "core.User": "fas fa-universal-access",  # Fixed model reference
        "core.Profile": "fas fa-user",  # Fixed model reference
        "blog.Category": "fas fa-folder",  # Added blog icons
        "blog.Subcategory": "fas fa-folder-open",
        "blog.News": "fas fa-newspaper",
        "blog.Advertisement": "fas fa-ad",
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
    "user_avatar": None,
}