const apiOffline = { News: "/news" };

const teacherLoggedIn = {
  Problems: "/problems",
  Shell: "/shell",
  Scoreboard: "/scoreboard",
  Classroom: "/classroom",
  News: "/news"
};

const teacherLoggedInNoCompetition = {
  Scoreboard: "/scoreboard",
  Classroom: "/classroom",
  News: "/news"
};

const userLoggedIn = {
  Problems: "/problems",
  Shell: "/shell",
  Scoreboard: "/scoreboard",
  News: "/news"
};

const userLoggedInNoCompetition = {
  Scoreboard: "/scoreboard",
  News: "/news"
};

const userNotLoggedIn = { News: "/news" };

const adminLoggedIn = { Management: "/management" };

const loadNavbar = function(renderNavbarLinks, renderNestedNavbarLinks) {
  const navbarLayout = {
    renderNavbarLinks,
    renderNestedNavbarLinks
  };

  apiCall("GET", "/api/v1/user")
    .success(userData =>
      apiCall("GET", "/api/v1/status")
        .success(function(competitionData) {
          navbarLayout.links = userNotLoggedIn;
          navbarLayout.status = userData;
          navbarLayout.topLevel = true;
          if (userData["logged_in"]) {
            if (userData["teacher"]) {
              if (competitionData["competition_active"]) {
                navbarLayout.links = teacherLoggedIn;
              } else {
                navbarLayout.links = teacherLoggedInNoCompetition;
              }
            } else {
              if (competitionData["competition_active"]) {
                navbarLayout.links = userLoggedIn;
              } else {
                navbarLayout.links = userLoggedInNoCompetition;
              }
            }
            if (userData["admin"]) {
              $.extend(navbarLayout.links, adminLoggedIn);
            }
          } else {
            $(".show-when-logged-out").css("display", "inline-block");
          }
          $("#navbar-links").html(renderNavbarLinks(navbarLayout));
          $("#navbar-item-logout").on("click", logout);
        })
        .fail(function() {
          navbarLayout.links = apiOffline;
          $("#navbar-links").html(renderNavbarLinks(navbarLayout));
        })
    )
    .fail(function() {
      navbarLayout.links = apiOffline;
      $("#navbar-links").html(renderNavbarLinks(navbarLayout));
    });
};

$(function() {
  const renderNavbarLinks = _.template(
    $("#navbar-links-template")
      .remove()
      .text()
  );
  const renderNestedNavbarLinks = _.template(
    $("#navbar-links-dropdown-template")
      .remove()
      .text()
  );

  loadNavbar(renderNavbarLinks, renderNestedNavbarLinks);
});