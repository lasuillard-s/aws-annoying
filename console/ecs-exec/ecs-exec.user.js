// ==UserScript==
// @name         AWS ECS Exec
// @namespace    mailto:lasuillard@gmail.com
// @version      2025.04.16
// @description  Add link to AWS SSM Session Manager for ECS container
// @author       lasuillard
// @source       https://raw.githubusercontent.com/lasuillard/aws-annoying/refs/heads/main/console/ecs-exec/ecs-exec.user.js
// @match        https://*.console.aws.amazon.com/ecs/v2/*
// @icon         data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==
// @grant        GM_log
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
        item[colName] = column; // Keep the HTML element for later use
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
    GM_log("Adding listener to table...");
    if (!table) {
      GM_log("Table is empty, skipping...");
      return null;
    }
    for (const row of table.rows) {
      const targetElement = row["Container name"].children[0];
      GM_log(`Adding click event listener to container: ${targetElement.textContent}`);

      // Style it like a link
      targetElement.style.textDecoration = "underline";
      targetElement.style.cursor = "pointer";

      // Attach on-click event listener to open the SSM Session Manager in new page
      // NOTE: This event listener works OK for list pages because the container table is updated in-place
      targetElement.onclick = function () {
        const taskInfo = getTaskInfo();
        const containerRuntimeId = row["Container runtime ID"].textContent;
        // Task in pending state could include containers not started yet
        // NOTE: The container could have exited even the runtime ID is not empty.
        //       We can check the container's status to be sure, but leaving it to future improvement
        //       to not make the script too complex, at least for now.
        if (!containerRuntimeId) {
          GM_log("Container runtime ID is empty, skipping...");
          return;
        }
        const ssmInstanceId = `ecs:${taskInfo.clusterName}_${taskInfo.taskId}_${containerRuntimeId}`;
        const ssmLink = `https://${taskInfo.region}.console.aws.amazon.com/systems-manager/session-manager/${ssmInstanceId}`;
        GM_log(`Opening SSM Session Manager link: ${ssmLink}`);
        window.open(ssmLink, "_blank");
      }
    }
  }

  // Task context
  // -------------------------------------------------------------------------
  // Get task info based on the current page
  function getTaskInfo() {
    const currentPage = new URL(location.href);
    let taskInfo = null;
    if (currentPage.pathname.match(/\/ecs\/v2\/clusters\/.*\/tasks\/.*\/configuration.*/)) {
      GM_log("Getting task info from detail page");
      taskInfo = getTaskInfoForDetailPage();
    } else if (currentPage.pathname.match(/\/ecs\/v2\/clusters\/.*\/tasks(?!.*(configuration)).*/)) {
      GM_log("Getting task info from list page");
      taskInfo = getTaskInfoForListPage();
    } else {
      GM_log(`There is no task info available for this page: ${currentPage.href}`);
      taskInfo = null;
    }
    GM_log(`Task info retrieved from page: ${JSON.stringify(taskInfo)}`);
    return taskInfo;
  }

  // Get task info from the detail page
  function getTaskInfoForDetailPage() {
    const arnNeighbor = document.evaluate(`//*[text()="ARN"]`, document).iterateNext();
    if (!arnNeighbor) {
      return null;
    }
    const arn = arnNeighbor.parentNode.parentNode.children[1].textContent;
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

  // Table may not be available immediately; wait for it appear and run the handler
  function waitForTableAndRun(handler) {
    GM_log("Waiting for table to appear...");
    const waitForTable = setInterval(() => {
      GM_log("Checking for table...");
      const tables = document.querySelectorAll("table");
      if (tables.length > 0) {
        GM_log("Table found! Running handler...");
        clearInterval(waitForTable);
        handler();
      }
    }, 1_000);
  }

  window.addEventListener("load", function () {
    GM_log("Page loaded");

    // Periodically check current URL; the site's internal navigation doesn't trigger script when needed
    let previousPage = null;

    // TODO(lasuillard): Could use `setTimeout` instead of `setInterval` for fine-tuned behavior
    //                   such as retry backoff, maximum retries, ...
    // See also: https://stackoverflow.com/questions/1280263/changing-the-interval-of-setinterval-while-its-running
    GM_log("Start checking for page changes...");
    setInterval(() => {
      GM_log("Checking for page change...");
      const currentPage = new URL(location.href);

      // If the page is the same as the previous one, do nothing
      if (previousPage?.href == currentPage.href) {
        return;
      }

      // If the page changed...
      GM_log(`Page changed: ${previousPage?.href} => ${currentPage.href}`);
      previousPage = currentPage;
      waitForTableAndRun(handlePage);
    }, 1_000);
  });

})();
