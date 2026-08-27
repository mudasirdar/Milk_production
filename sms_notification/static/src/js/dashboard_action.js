/** @odoo-module **/

import { Component, useState, onMounted, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

const D3_COLORS = [
    "#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"
];

export class SMSNotificationDashboard extends Component {
    static template = "sms_notification.dashboard_template";

    setup() {
        this.actionService = useService("action");
        this.state = useState({
            line_data: { labels: [], data: [] },
            gateway_data: {},
            total_count: 0,
            sent_count: 0,
            delivered_count: 0,
            undelivered_count: 0,
            failed_count: 0,
            connected_count: 0,
        });

        onWillStart(async () => {
            if (typeof Chart === "undefined") {
                await loadJS("/web/static/lib/Chart/Chart.js");
            }
            await this.fetchData();
        });

        onMounted(() => {
            this.renderLineGraph();
            this.renderPieGraph();
        });
    }

    gatewayKeys() {
        return Object.keys(this.state.gateway_data);
    }

    async fetchData(line_stage = "all", pie_stage = "total", days = 7) {
        const result = await rpc("/sms_notification/dashboard_data", { line_stage, pie_stage, days });
        Object.assign(this.state, {
            line_data: result.line_data,
            gateway_data: result.gateway_data,
            total_count: result.total_count,
            sent_count: result.sent_count,
            delivered_count: result.delivered_count,
            undelivered_count: result.undelivered_count,
            failed_count: result.failed_count,
            connected_count: result.connected_count,
        });
    }

    async onLineGraphChange() {
        const lineObj = document.getElementById("line_obj_change");
        const lineDate = document.getElementById("line_date_change");
        const pieObj = document.getElementById("pie_obj_change");
        const selected = lineObj ? lineObj.value : "all";
        const labelMap = { new: "New", sent: "Sent", delivered: "Delivered", undelivered: "Undelivered", failed: "Failed" };
        const labelEl = document.getElementById("line_chart_label");
        if (labelEl) labelEl.textContent = labelMap[selected] || "";
        await this.fetchData(
            selected,
            parseInt(pieObj ? pieObj.value : "0"),
            parseInt(lineDate ? lineDate.value : "7"),
        );
        this.renderLineGraph();
    }

    onPieGraphChange() {
        const pieObj = document.getElementById("pie_obj_change");
        const selected = pieObj ? pieObj.value : "total";
        const labelEl = document.getElementById("pie_chart_label");
        if (labelEl) labelEl.textContent = selected.charAt(0).toUpperCase() + selected.slice(1);
        this.renderPieGraph(selected);
    }

    _resetCanvas(id) {
        const el = document.getElementById(id);
        if (!el) return;
        const newCanvas = document.createElement("canvas");
        newCanvas.id = id;
        el.replaceWith(newCanvas);
    }

    renderLineGraph() {
        this._resetCanvas("line_chart");
        if (!document.getElementById("line_chart")) return;
        new Chart("line_chart", {
            type: "line",
            data: {
                labels: this.state.line_data.labels || [],
                datasets: (this.state.line_data.data || []).map(i => ({
                    backgroundColor: D3_COLORS[1],
                    borderColor: D3_COLORS[0],
                    data: i.count,
                    label: i.state,
                    fill: false,
                })),
            },
            options: {
                maintainAspectRatio: false,
                legend: { display: false },
                scales: {
                    xAxes: [{ gridLines: { display: false } }],
                    yAxes: [{ gridLines: { display: false }, ticks: { precision: 0 } }],
                },
            },
        });
    }

    renderPieGraph(obj = "total") {
        this._resetCanvas("pie_chart");
        if (!document.getElementById("pie_chart")) return;
        new Chart("pie_chart", {
            type: "pie",
            data: {
                labels: Object.keys(this.state.gateway_data),
                datasets: [{
                    backgroundColor: Object.values(this.state.gateway_data).map((_, i) => D3_COLORS[i % 20]),
                    data: Object.values(this.state.gateway_data).map(i => i[obj + "_count"] || 0),
                }],
            },
            options: {
                maintainAspectRatio: false,
                cutoutPercentage: 75,
                legend: { position: "bottom", labels: { usePointStyle: true } },
            },
        });
    }

    onAction(ev) {
        ev.preventDefault();
        const action = ev.currentTarget.dataset.action;
        if (action === "send_sms") {
            this.actionService.doAction({
                name: "Send SMS",
                type: "ir.actions.act_window",
                res_model: "wk.sms.sms",
                views: [[false, "form"]],
                target: "new",
            });
        } else if (action === "configuration") {
            this.actionService.doAction({
                name: "Gateway Configuration",
                type: "ir.actions.act_window",
                res_model: "sms.mail.server",
                views: [[false, "form"]],
                target: "new",
            });
        }
    }
}

registry.category("actions").add("sms_notification.dashboard", SMSNotificationDashboard);
