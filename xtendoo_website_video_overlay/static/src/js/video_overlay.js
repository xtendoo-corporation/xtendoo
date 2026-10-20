/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.XtendooVideoOverlay = publicWidget.Widget.extend({
    selector: '.s_video_overlay',
    events: {
        'click .o_video_play_btn': '_onClickPlay',
    },

    start: function () {
        return this._super.apply(this, arguments);
    },

    _onClickPlay: function (ev) {
        ev.preventDefault();
        
        const videoSrc = this.$target.attr('data-video-src');
        if (!videoSrc) {
            console.warn("Xtendoo: No se configuró URL de vídeo interno en este snippet.");
            return;
        }

        // 1. Inicialización y/o recuperación del modal global
        let $modal = $('#XtendooVideoOverlayGlobalModal');
        if ($modal.length === 0) {
            const modalHtml = `
                <div class="modal fade" id="XtendooVideoOverlayGlobalModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-centered">
                        <div class="modal-content bg-transparent border-0 shadow-none">
                            <div class="modal-header border-0 pb-0 justify-content-end" style="z-index:10;">
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body p-0 text-center position-relative">
                                <video id="XtendooVideoOverlayGlobalPlayer" class="w-100 rounded shadow-lg" controls disablePictureInPicture controlsList="nodownload">
                                    <source src="" type="video/mp4" />
                                    Tu navegador no soporta video HTML5.
                                </video>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            $(document.body).append(modalHtml);
            $modal = $('#XtendooVideoOverlayGlobalModal');

            // Limpieza y reseteo absoluto del vídeo cuando se cierra el modal
            $modal.on('hidden.bs.modal', function () {
                const player = document.getElementById('XtendooVideoOverlayGlobalPlayer');
                if (player) {
                    player.pause();
                    player.currentTime = 0;
                    // Eliminar source obliga al buffer a cortar cualquier descarga residente en background
                    const source = player.querySelector('source');
                    if (source) source.src = '';
                    player.load();
                }
            });

            // Autocerrar el modal cuando termine el vídeo
            const globalPlayer = document.getElementById('XtendooVideoOverlayGlobalPlayer');
            if (globalPlayer) {
                globalPlayer.addEventListener('ended', function () {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                        let bsModal = bootstrap.Modal.getInstance($modal[0]);
                        if (bsModal) bsModal.hide();
                    } else if ($.fn.modal) {
                        $modal.modal('hide');
                    }
                });
            }
        }

        // 2. Carga dinámica de la fuente correcta y autoplay
        const player = document.getElementById('XtendooVideoOverlayGlobalPlayer');
        if (player) {
            const source = player.querySelector('source');
            source.src = videoSrc;
            player.load();
            
            const playPromise = player.play();
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    console.log("Autoplay fue interrumpido (probablemente bloque web no interactuado) o la URL del vídeo es errónea.", error);
                });
            }
        }

        // 3. Apertura del modal en Bootstrap 5 (Core Odoo 18)
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            let bsModal = bootstrap.Modal.getInstance($modal[0]);
            if (!bsModal) bsModal = new bootstrap.Modal($modal[0]);
            bsModal.show();
        } else if ($.fn.modal) {
            $modal.modal('show');
        }
    }
});
