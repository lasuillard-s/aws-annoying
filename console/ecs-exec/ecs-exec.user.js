// ==UserScript==
// @name         AWS ECS Exec
// @namespace    mailto:lasuillard@gmail.com
// @version      2025.03.13
// @description  Add link to AWS SSM Session Manager for ECS container
// @author       lasuillard
// @source       https://raw.githubusercontent.com/lasuillard/aws-annoying/refs/heads/main/console.ecs-exec.user.js
// @match        https://*.console.aws.amazon.com/ecs/v2/*
// @icon         data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  // Get ARN from page
  function getARN() {
    const arnNeighbor = document.evaluate(`//div[text()="ARN"]`, document).iterateNext();
    if (!arnNeighbor) return null;

    const arn = arnNeighbor.parentNode.children[1].textContent;
    return arn;
  }

  // Convert HTML table to JSON array of objects
  function getTableData(table) {
    const header = [...table.querySelectorAll("thead th")];
    const headerNames = header.map((item) => item.textContent);
    const rows = [...table.querySelectorAll("tbody tr")];
    const result = [];
    for (const row of rows) {
      const columns = [...row.querySelectorAll("td")];
      const item = {};
      for (const [idx, column] of columns.entries()) {
        let colName = headerNames[idx];
        item[colName] = column;
      }
      result.push(item);
    }
    return result;
  }

  // Find containers table and add hyperlink to SSM Session Manager (web console)
  function addLinkToSessionManager() {
    const arn = getARN();
    if (!arn) return;

    const [, , , region, accountId, taskPart] = arn.split(":");
    const [, clusterName, taskId] = taskPart.split("/");

    const tables = document.querySelectorAll("table");
    for (const table of tables) {
      if (!table.textContent.startsWith("Container")) continue;

      const tableData = getTableData(table);
      for (const row of tableData) {
        const containerName = row["Container name"].textContent;
        const containerRuntimeId = row["Container runtime ID"].textContent;
        const ssmInstanceId = `ecs:${clusterName}_${taskId}_${containerRuntimeId}`;
        const ssmLink = `https://${region}.console.aws.amazon.com/systems-manager/session-manager/${ssmInstanceId}`;
        row["Container name"].children[0].innerHTML = `<a href="${ssmLink}" target="_blank">${containerName}</a>`;
      }
    }
  }

  // Table may not available immediately; wait for it
  function waitForTableAndRun(func) {
    const waitForTable = setInterval(() => {
      const tables = document.querySelectorAll("table");
      if (tables.length > 0) {
        clearInterval(waitForTable);
        addLinkToSessionManager();
      }
    }, 1_000);
  }

  // Periodically check current URL; the site's internal navigation doesn't trigger script when needed
  window.addEventListener("load", function () {
    const pattern = new RegExp(/https:\/\/.*\.console\.aws\.amazon\.com\/ecs\/v2\/clusters\/.*\/tasks\/.*\/configuration.*/);
    let previousPage = null;
    setInterval(() => {
      let currentPage = location.href;
      if (previousPage == currentPage) return;

      previousPage = currentPage;
      if (location.href.match(pattern)) {
        waitForTableAndRun();
      }
    }, 1_000);
  });
})();
