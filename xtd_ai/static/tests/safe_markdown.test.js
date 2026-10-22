import {animationFrame, describe, expect, test} from "@odoo/hoot";
import {click, edit, press} from "@odoo/hoot-dom";
import {
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {parseInline, parseSafeMarkdown} from "@xtd_ai/js/safe_markdown.esm";
import {defineMailModels} from "@mail/../tests/mail_test_helpers";
import {reactive} from "@odoo/owl";
import {ChatWindow, SafeText} from "@xtd_ai/js/chat_window.esm";
import {ChatApp} from "@xtd_ai/js/chat_app.esm";
import {ChatSystray} from "@xtd_ai/js/chat_systray.esm";
import {user} from "@web/core/user";

defineMailModels();

describe("xtd_ai safe renderer", () => {
    test("inline bold and italics", () => {
        expect(parseInline("a **b** *c* d")).toEqual([
            {text: "a ", bold: false, italic: false},
            {text: "b", bold: true, italic: false},
            {text: " ", bold: false, italic: false},
            {text: "c", bold: false, italic: true},
            {text: " d", bold: false, italic: false},
        ]);
    });

    test("unbalanced markers and math stay literal", () => {
        expect(
            parseInline("2 * 3 * 4")
                .map((s) => s.text)
                .join("")
        ).toBe("2 * 3 * 4");
        expect(parseInline("**abierto")[0]).toEqual({
            text: "**abierto",
            bold: false,
            italic: false,
        });
    });

    test("lists, paragraphs and line breaks", () => {
        const blocks = parseSafeMarkdown("Hola\nmundo\n\n- uno\n- dos\n\n1. a\n2) b");
        expect(blocks.map((b) => b.type)).toEqual(["p", "ul", "ol"]);
        expect(blocks[0].inline.some((s) => s.br)).toBe(true);
        expect(blocks[1].items).toHaveLength(2);
        expect(blocks[2].items).toHaveLength(2);
    });

    test("pipe table", () => {
        const [table] = parseSafeMarkdown(
            "| A | B |\n|---|---|\n| 1 | **2** |\n| 3 | 4 |"
        );
        expect(table.type).toBe("table");
        expect(table.header).toHaveLength(2);
        expect(table.rows).toHaveLength(2);
        expect(table.rows[0][1][0].bold).toBe(true);
    });

    test("html, images and links are never interpreted", async () => {
        const text =
            "<script>alert(1)</script> <img src=x onerror=alert(2)> [clic](https://evil.example) " +
            "![i](https://evil.example/x.png) https://evil.example/a";
        await mountWithCleanup(SafeText, {props: {text}});
        expect(".o_xtd_ai_text script").toHaveCount(0);
        expect(".o_xtd_ai_text img").toHaveCount(0);
        expect(".o_xtd_ai_text a").toHaveCount(0);
        expect(".o_xtd_ai_text").toHaveText(text);
    });

    test("html in table cells and lists is escaped", async () => {
        await mountWithCleanup(SafeText, {
            props: {text: "- <b>x</b>\n\n| <i>h</i> |\n|---|\n| <a href=1>c</a> |"},
        });
        expect(
            ".o_xtd_ai_text b, .o_xtd_ai_text i:not(em), .o_xtd_ai_text a"
        ).toHaveCount(0);
        expect(".o_xtd_ai_text li").toHaveText("<b>x</b>");
    });

    const baseState = (extra = {}) =>
        reactive({
            // False: the web client's own host must not render a second window
            isOpen: false,
            minimized: false,
            loading: false,
            busy: false,
            conversationId: 1,
            currentId: 1,
            conversationState: "open",
            runningRunId: null,
            error: null,
            banner: null,
            draft: "",
            attachments: [],
            suggestions: [],
            conversations: [],
            messages: [],
            settings: {forced: false, confirm_writes: true},
            ...extra,
        });

    const message = (extra = {}) => ({
        id: 1,
        role: "assistant",
        date: "2026-01-01 10:00:00",
        run_id: false,
        run_state: false,
        body: "hola",
        record_refs: [],
        pending_actions: [],
        attachments: [],
        ...extra,
    });

    test("window: thinking state, confirmation card, forced toggle, links only from refs", async () => {
        const calls = [];
        const state = baseState({
            runningRunId: 7,
            settings: {forced: true, confirm_writes: true},
            messages: [
                message({
                    run_id: 7,
                    run_state: "running",
                    body: "Mira https://evil.example **hecho**",
                    record_refs: [
                        {
                            model: "res.partner",
                            id: 5,
                            name: "Cliente",
                            url: "/odoo/res.partner/5",
                        },
                    ],
                    pending_actions: [
                        {
                            id: 3,
                            title: "Crear contacto",
                            summary: "Crear contacto «X»",
                            state: "pending",
                            lines: [{field: "name", value: "X"}],
                            result: null,
                            error: false,
                            actionable: true,
                        },
                    ],
                }),
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            confirmAction: (id) => calls.push(["confirm", id]),
            cancelAction: (id) => calls.push(["cancel", id]),
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_thinking").toHaveCount(1);
        expect(".o_xtd_ai_text a").toHaveCount(0);
        expect("a.o_xtd_ai_ref").toHaveCount(1);
        expect("a.o_xtd_ai_ref").toHaveAttribute("href", "/odoo/res.partner/5");
        await click(".o_xtd_ai_menu_toggle");
        await animationFrame();
        expect(".o_xtd_ai_confirm_toggle input").toHaveAttribute("disabled", "");
        expect(".o_xtd_ai_card .o_xtd_ai_card_summary").toHaveText(
            "Crear contacto «X»"
        );
        expect(".o_xtd_ai_send").toHaveAttribute("disabled", "");
        await click(".o_xtd_ai_confirm");
        await animationFrame();
        expect(calls).toEqual([["confirm", 3]]);
    });

    test("window: minimise hides the body, close and expand are available", async () => {
        const calls = [];
        const state = baseState();
        mockService("xtd_ai.chat", {
            state,
            toggleMinimize: () => {
                state.minimized = !state.minimized;
            },
            close: () => calls.push("close"),
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_window .o_xtd_ai_title").toHaveText("Asistente IA");
        expect(".o_xtd_ai_conversation").toHaveCount(1);
        expect(".o_xtd_ai_expand").toHaveCount(1);
        await click(".o_xtd_ai_minimize");
        await animationFrame();
        expect(".o_xtd_ai_conversation").toHaveCount(0);
        expect(".o_xtd_ai_window.o_xtd_ai_minimized").toHaveCount(1);
        expect(".o_xtd_ai_header").toHaveCount(1);
        await click(".o_xtd_ai_minimize");
        await animationFrame();
        expect(".o_xtd_ai_conversation").toHaveCount(1);
        await click(".o_xtd_ai_close");
        await animationFrame();
        expect(calls).toEqual(["close"]);
    });

    test("empty state shows the role chips; clicking one sends it, a prefill chip fills the input", async () => {
        const calls = [];
        const state = baseState({
            suggestions: [
                {key: "a", text: "¿Qué presupuestos tengo en borrador?", send: true},
                {key: "b", text: "¿Qué stock hay del producto ", send: false},
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            send: (text) => calls.push(text),
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_empty h5").toHaveText("Asistente IA");
        expect(".o_xtd_ai_empty p").toHaveText("Tu ayudante para el día a día en Odoo");
        expect(".o_xtd_ai_chip").toHaveCount(2);
        await click(".o_xtd_ai_chip:eq(0)");
        await animationFrame();
        expect(calls).toEqual(["¿Qué presupuestos tengo en borrador?"]);
        await click(".o_xtd_ai_chip:eq(1)");
        await animationFrame();
        expect(state.draft).toBe("¿Qué stock hay del producto ");
        expect(calls).toHaveLength(1);
    });

    test("attachment chips are removable and sent attachments show in the bubble", async () => {
        const calls = [];
        const state = baseState({
            attachments: [
                {
                    key: "k1",
                    id: 5,
                    name: "factura.pdf",
                    mimetype: "application/pdf",
                    size: 2048,
                },
            ],
            messages: [
                message({
                    id: 2,
                    role: "user",
                    body: "Crea la factura",
                    attachments: [
                        {
                            id: 4,
                            name: "antigua.png",
                            mimetype: "image/png",
                            size: 1048576,
                            url: "/web/content/4?download=true",
                        },
                    ],
                }),
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            removeAttachment: (key) => {
                calls.push(key);
                state.attachments = [];
            },
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_file_chip").toHaveCount(1);
        expect(".o_xtd_ai_file_chip .o_xtd_ai_file_name").toHaveText("factura.pdf");
        expect(".o_xtd_ai_file_chip .fa-file-pdf-o").toHaveCount(1);
        // Attachments alone are enough to enable the send button
        expect(".o_xtd_ai_send").not.toHaveAttribute("disabled", "");
        expect("a.o_xtd_ai_msg_file").toHaveAttribute(
            "href",
            "/web/content/4?download=true"
        );
        expect("a.o_xtd_ai_msg_file .fa-file-image-o").toHaveCount(1);
        await click(".o_xtd_ai_file_remove");
        await animationFrame();
        expect(calls).toEqual(["k1"]);
        expect(".o_xtd_ai_file_chip").toHaveCount(0);
        expect(".o_xtd_ai_send").toHaveAttribute("disabled", "");
    });

    test("Enter sends the draft, Shift+Enter does not", async () => {
        const calls = [];
        const state = baseState();
        mockService("xtd_ai.chat", {
            state,
            send: () => calls.push("send"),
        });
        await mountWithCleanup(ChatWindow);
        await click(".o_xtd_ai_input");
        await animationFrame();
        await edit("hola");
        await animationFrame();
        expect(".o_xtd_ai_send").not.toHaveAttribute("disabled", "");
        await press(["shift", "enter"]);
        await animationFrame();
        expect(calls).toHaveLength(0);
        await press("enter");
        await animationFrame();
        expect(calls).toEqual(["send"]);
    });

    test("record links open inside the web client, ctrl+click keeps the browser default", async () => {
        const calls = [];
        const state = baseState({
            messages: [
                message({
                    record_refs: [
                        {
                            model: "sale.order",
                            id: 60,
                            name: "S00060",
                            url: "/odoo/sale.order/60",
                        },
                    ],
                }),
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            openRecord: (model, id) => calls.push([model, id]),
        });
        await mountWithCleanup(ChatWindow);
        expect("a.o_xtd_ai_ref").toHaveAttribute("href", "/odoo/sale.order/60");
        expect("a.o_xtd_ai_ref").not.toHaveAttribute("target");
        await click("a.o_xtd_ai_ref");
        await animationFrame();
        expect(calls).toEqual([["sale.order", 60]]);
        // Ctrl+click: our handler must not navigate in-app. Stop the browser default
        // too (it would leave the test page), after our handler had its chance.
        const stopDefault = (ev) => ev.preventDefault();
        document.addEventListener("click", stopDefault);
        try {
            document.querySelector("a.o_xtd_ai_ref").dispatchEvent(
                new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    ctrlKey: true,
                })
            );
            await animationFrame();
        } finally {
            document.removeEventListener("click", stopDefault);
        }
        expect(calls).toEqual([["sale.order", 60]]); // No second in-app navigation
    });

    test("the input box is emptied even when Enter comes in the same frame as typing", async () => {
        // Regression: typing (or pasting) and pressing Enter before Owl rendered left
        // the sent text in the box, because t-model saw no change from "" to "".
        const state = baseState();
        mockService("xtd_ai.chat", {
            state,
            send: async () => {
                state.draft = "";
            },
        });
        await mountWithCleanup(ChatWindow);
        await click(".o_xtd_ai_input");
        await animationFrame();
        await edit("hola rápido");
        await press("enter");
        await animationFrame();
        expect(".o_xtd_ai_input").toHaveValue("");
    });

    test("new-conversation banner links to the previous one and can be dismissed", async () => {
        const calls = [];
        const state = baseState({banner: {previousId: 3}});
        mockService("xtd_ai.chat", {
            state,
            viewPrevious: () => calls.push("previous"),
            dismissBanner: () => {
                state.banner = null;
            },
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_banner").toHaveCount(1);
        await click(".o_xtd_ai_banner_link");
        await animationFrame();
        expect(calls).toEqual(["previous"]);
        await click(".o_xtd_ai_banner_close");
        await animationFrame();
        expect(".o_xtd_ai_banner").toHaveCount(0);
    });

    test("closed conversation is read-only: no input, back link, no confirm buttons", async () => {
        const calls = [];
        const state = baseState({
            conversationId: 7,
            conversationState: "closed",
            banner: {previousId: 7},
            messages: [
                message({
                    pending_actions: [
                        {
                            id: 3,
                            title: "Crear contacto",
                            summary: "Crear X",
                            state: "pending",
                            actionable: false,
                            lines: [],
                            result: null,
                            error: false,
                        },
                    ],
                }),
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            backToCurrent: () => calls.push("back"),
        });
        await mountWithCleanup(ChatWindow);
        expect(".o_xtd_ai_input").toHaveCount(0);
        expect(".o_xtd_ai_attach").toHaveCount(0);
        expect(".o_xtd_ai_banner").toHaveCount(0);
        expect(".o_xtd_ai_readonly_bar").toHaveCount(1);
        expect(".o_xtd_ai_confirm").toHaveCount(0);
        expect(".o_xtd_ai_discard").toHaveCount(0);
        expect(".o_xtd_ai_card_state").toHaveCount(1);
        await click(".o_xtd_ai_back_current");
        await animationFrame();
        expect(calls).toEqual(["back"]);
    });

    test("app lists history, searches by title and selects a past conversation", async () => {
        const calls = [];
        const state = baseState({
            isOpen: false,
            conversationId: 9,
            conversations: [
                {
                    id: 9,
                    name: "Nueva conversación",
                    preview: "",
                    state: "open",
                    message_count: 0,
                    date: "2026-01-02 10:00:00",
                },
                {
                    id: 4,
                    name: "Facturas de marzo",
                    preview: "Tienes 3 facturas",
                    state: "closed",
                    message_count: 6,
                    date: "2026-01-01 10:00:00",
                },
            ],
        });
        mockService("xtd_ai.chat", {
            state,
            close: () => undefined,
            openApp: () => calls.push("openApp"),
            selectConversation: (id) => calls.push(["select", id]),
            showCurrent: () => calls.push("current"),
            newConversation: () => calls.push("new"),
        });
        await mountWithCleanup(ChatApp);
        expect(".o_xtd_ai_history_item").toHaveCount(2);
        expect(".o_xtd_ai_history_title:eq(1)").toHaveText("Facturas de marzo");
        expect(".o_xtd_ai_history_preview:eq(1)").toHaveText("Tienes 3 facturas");
        await click(".o_xtd_ai_search");
        await animationFrame();
        await edit("marzo");
        await animationFrame();
        expect(".o_xtd_ai_history_item").toHaveCount(1);
        await click(".o_xtd_ai_history_item");
        await animationFrame();
        await click(".o_xtd_ai_search");
        await animationFrame();
        await edit("");
        await animationFrame();
        await click(".o_xtd_ai_history_item:eq(0)");
        await animationFrame();
        await click(".o_xtd_ai_history .o_xtd_ai_new");
        await animationFrame();
        expect(calls).toEqual(["openApp", ["select", 4], "current", "new"]);
    });
});

describe("xtd_ai systray", () => {
    // Regression: the systray icon used ChatLogo without declaring it, which
    // crashed the whole web client for every AI user. Mount it for real.
    test("systray icon renders with its logo and toggles the window", async () => {
        patchWithCleanup(user, {hasGroup: async () => true});
        const calls = [];
        mockService("xtd_ai.chat", {
            state: reactive({isOpen: false}),
            toggle: () => calls.push("toggle"),
        });
        await mountWithCleanup(ChatSystray);
        await animationFrame();
        expect("button.o_xtd_ai_toggle").toHaveCount(1);
        expect("button.o_xtd_ai_toggle svg, button.o_xtd_ai_toggle img").toHaveCount(1);
        await click("button.o_xtd_ai_toggle");
        expect(calls).toEqual(["toggle"]);
    });

    test("systray icon hidden without the AI group", async () => {
        patchWithCleanup(user, {hasGroup: async () => false});
        mockService("xtd_ai.chat", {
            state: reactive({isOpen: false}),
            toggle: () => undefined,
        });
        await mountWithCleanup(ChatSystray);
        await animationFrame();
        expect("button.o_xtd_ai_toggle").toHaveCount(0);
    });
});
