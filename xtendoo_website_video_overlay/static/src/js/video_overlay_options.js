/** @odoo-module */

import options from '@web_editor/js/editor/snippets.options';
import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";

options.registry.XtendooVideoOverlayConfig = options.Class.extend({
    events: {
        'click .o_we_select_video': '_onSelectVideo',
    },

    _onSelectVideo: function (ev) {
        ev.preventDefault();
        
        const $editable = this.$target.closest('.o_editable');
        const resModel = $editable.length ? $editable.data('oe-model') : 'ir.ui.view';
        const resId = $editable.length ? $editable.data('oe-id') : 0;
        
        this.call("dialog", "add", MediaDialog, {
            noImages: true,
            noVideos: false, // Permitimos a Odoo manejar el diálogo de vídeos/documentos normal
            noIcons: true,
            noDocuments: false, // Documentos activa la subida de archivos (MP4) locales
            res_model: resModel,
            res_id: resId,
            save: (mediaElements) => {
                // odoo MediaDialog return puede ser un DOM element (ej. <a>) si se subió como Document,
                // o un <iframe> si se usó la pestaña Video (youtube).
                // Extraemos src o href:
                if (!mediaElements) return;
                let elem = Array.isArray(mediaElements) ? mediaElements[0] : mediaElements;
                let src = elem.getAttribute('href') || elem.getAttribute('src');
                
                if (src) {
                    this.$target.attr('data-video-src', src);
                    
                    // Actualizar dinámicamente el src del vídeo miniatura para que cargue el primer frame al vuelo
                    let $posterVideo = this.$target.find('.o_video_poster_video');
                    if ($posterVideo.length) {
                        $posterVideo.attr('src', src);
                    }

                    // Disparamos evento para que el DOM se marque como sucio/modificado y Odoo lo guarde en BD
                    this.$target.trigger('content_changed');
                }
            }
        });
    },

});
