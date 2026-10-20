import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class VideoOverlayOption extends BaseOptionComponent {
    static template = "xtendoo_website_video_overlay.VideoOverlayOption";
    static selector = ".s_video_overlay";
}

class VideoOverlayOptionPlugin extends Plugin {
    static id = "xtendooVideoOverlayOption";
    resources = {
        builder_options: [withSequence(before(SNIPPET_SPECIFIC_END), VideoOverlayOption)],
        builder_actions: {
            XtendooSelectVideoAction,
        },
    };
}

export class XtendooSelectVideoAction extends BuilderAction {
    static id = "xtendooSelectVideo";
    static dependencies = ["media"];

    load() {
        let result;
        return this.dependencies.media
            .openMediaDialog({
                // DOCUMENTS permite subir MP4 locales; VIDEOS el selector estándar.
                visibleTabs: ["DOCUMENTS", "VIDEOS"],
                save: (mediaElements) => {
                    const elem = mediaElements && (mediaElements[Symbol.iterator] ? [...mediaElements][0] : mediaElements);
                    const src = elem && (elem.getAttribute("href") || elem.getAttribute("src"));
                    if (src) {
                        result = { src };
                    }
                },
            })
            .then(() => result || { cancel: true });
    }

    apply({ editingElement, loadResult: { src, cancel } = {} }) {
        if (cancel || !src) {
            return;
        }
        editingElement.dataset.videoSrc = src;
        const posterVideoEl = editingElement.querySelector(".o_video_poster_video");
        if (posterVideoEl) {
            posterVideoEl.setAttribute("src", src);
        }
    }
}

registry.category("website-plugins").add(VideoOverlayOptionPlugin.id, VideoOverlayOptionPlugin);
