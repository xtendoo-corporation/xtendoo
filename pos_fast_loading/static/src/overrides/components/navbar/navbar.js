/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { SynchNotificationWidget } from "@pos_fast_loading/app/SynchNotificationWidget/SynchNotificationWidget"

patch(Navbar, {
    components: { ...Navbar.components, SynchNotificationWidget },
});