document.addEventListener('DOMContentLoaded', function() {
    // Initialize all Materialize components
    M.AutoInit();

    // Initialize textareas
    var textareas = document.querySelectorAll('.materialize-textarea');
    textareas.forEach(function(textarea) {
        M.textareaAutoResize(textarea);
    });

    // Initialize tooltips
    var tooltips = document.querySelectorAll('.tooltipped');
    M.Tooltip.init(tooltips);

    // Initialize sidenav
    var sidenavs = document.querySelectorAll('.sidenav');
    M.Sidenav.init(sidenavs);
});
