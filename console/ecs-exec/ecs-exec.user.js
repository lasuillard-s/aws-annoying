// ==UserScript==
// @name         AWS ECS Exec
// @namespace    mailto:lasuillard@gmail.com
// @version      2025.03.20
// @description  Add link to AWS SSM Session Manager for ECS container
// @author       lasuillard
// @source       https://raw.githubusercontent.com/lasuillard/aws-annoying/refs/heads/main/console/ecs-exec/ecs-exec.user.js
// @match        https://*.console.aws.amazon.com/ecs/v2/*
// @icon         data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  // Common utils
  // -------------------------------------------------------------------------
  // Convert HTML table into JSON object
  function parseTable(table) {
    const header = [...table.querySelectorAll("thead th")];
    const headerNames = header.map((item) => item.textContent);
    const rows = [...table.querySelectorAll("tbody tr")];
    const result = [];
    for (const row of rows) {
      const columns = [...row.querySelectorAll("td")];
      const item = {};
      for (const [idx, column] of columns.entries()) {
        let colName = headerNames[idx];
        item[colName] = column;  // Keep the HTML element for later use
      }
      result.push(item);
    }
    return { header: headerNames, rows: result };
  }

  // Find the table containing the containers
  function findContainersTable() {
    const tables = document.querySelectorAll("table");
    for (const table of tables) {
      const parsedTable = parseTable(table);

      // ! This may work only for English version of the page...
      // ! AWS web console does not include any reliable identifier for the elements
      if (parsedTable.header.includes("Container name") && parsedTable.header.includes("Container runtime ID")) {
        return parsedTable;
      }
    }
    return null;
  }

  // Add click listener to the container name to open new page for Session Manager web
  function addListenerToTable(table, taskInfo) {
    if (!table) {
      return null;
    }
    for (const row of table.rows) {
      const targetElement = row["Container name"].children[0];

      // Style it like a link
      targetElement.style.textDecoration = "underline";
      targetElement.style.cursor = "pointer";

      // Attach on-click event listener to open the SSM Session Manager in new page
      targetElement.onclick = function () {
        const taskInfo = getTaskInfo();
        const containerRuntimeId = row["Container runtime ID"].textContent;
        const ssmInstanceId = `ecs:${taskInfo.clusterName}_${taskInfo.taskId}_${containerRuntimeId}`;
        const ssmLink = `https://${taskInfo.region}.console.aws.amazon.com/systems-manager/session-manager/${ssmInstanceId}`;
        window.open(ssmLink, "_blank");
      }
    }
  }

  // Table may not be available immediately; wait for it appear and run the handler
  function waitForTableAndRun(handler) {
    const waitForTable = setInterval(() => {
      const tables = document.querySelectorAll("table");
      if (tables.length > 0) {
        clearInterval(waitForTable);
        handler();
      }
    }, 1_000);
  }

  // Task context
  // -------------------------------------------------------------------------
  // Get task info based on the current page
  function getTaskInfo() {
    const currentPage = new URL(location.href);
    if (currentPage.pathname.match(/\/ecs\/v2\/clusters\/.*\/tasks\/.*\/configuration.*/)) {
      return getTaskInfoForDetailPage();
    }
    if (currentPage.pathname.match(/\/ecs\/v2\/clusters\/.*\/tasks(?!.*(configuration)).*/)) {
      return getTaskInfoForListPage();
    }
    return null;
  }

  // Get task info from the detail page
  function getTaskInfoForDetailPage() {
    const arnNeighbor = document.evaluate(`//div[text()="ARN"]`, document).iterateNext();
    if (!arnNeighbor) {
      return null;
    }
    const arn = arnNeighbor.parentNode.children[1].textContent;
    const [, , , region, , taskPart] = arn.split(":");
    const [, clusterName, taskId] = taskPart.split("/");

    return { region, clusterName, taskId };
  }

  // Get task info from the list page
  function getTaskInfoForListPage() {
    const match = location.href.match(/https:\/\/(.*?)\.console\.aws\.amazon\.com\/.*\/clusters\/(.*?)\/.*/);
    if (!match) {
      return null;
    }
    const [, region, clusterName] = match;

    // ! This may work only for English version of the page... but can't find reliable way to get it
    // ? Could use task ID's pattern (/[a-z0-9]{64}/) to find it (if necessary)
    const taskIdHeader = document.evaluate(
      '//*[starts-with(text(), "Containers for task")]', document, null, XPathResult.ANY_TYPE, null
    ).iterateNext();
    const [, taskId] = taskIdHeader.textContent.match(/Containers for task (.*)/);

    return { region, clusterName, taskId };
  }

  // Entrypoint
  // -------------------------------------------------------------------------
  function handlePage() {
    const taskInfo = getTaskInfoForDetailPage();
    const table = findContainersTable();
    addListenerToTable(table, taskInfo);
  }

  window.addEventListener("load", function () {
    // Periodically check current URL; the site's internal navigation doesn't trigger script when needed
    let previousPage = null;

    // TODO(lasuillard): Could use `setTimeout` instead of `setInterval` for fine-tuned behavior
    //                   such as retry backoff, maximum retries, ...
    // See also: https://stackoverflow.com/questions/1280263/changing-the-interval-of-setinterval-while-its-running
    setInterval(() => {
      const currentPage = new URL(location.href);

      // If the page is the same as the previous one, do nothing
      if (previousPage?.href == currentPage.href) {
        return;
      }

      // If the page changed...
      previousPage = currentPage;
      waitForTableAndRun(handlePage);
    }, 1_000);
  });

})();
