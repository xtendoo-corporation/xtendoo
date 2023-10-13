/** @odoo-module **/

import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { registry } from "@web/core/registry";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { patch } from "web.utils";


patch(Many2ManyBinaryField.prototype, "odx_m2m_attachment_preview", {

setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.operations = useX2ManyCrud(() => this.props.value, true);
    },

    onFilePreview: function (fileID) {
        var fileClass = '.attachment-preview-'+ fileID;
        var clickedElement = $(fileClass);
        var mimetype = clickedElement.attr('data-mimetype');
        var fileURL = clickedElement.attr('data-url');
        if (mimetype == 'image/jpeg') { this._previewImage(fileID) }
        else if (mimetype == 'image/jpg') { this._previewImage(fileID)}
        else if (mimetype == 'video/mp4') { this._previewVideo(fileID) }
        else if (mimetype == 'image/png') { this._previewImage(fileID) }
        else if (mimetype == 'application/pdf') { this._previewPDF(fileID) }
        else { this._downloadFile(fileURL) }
    },

    _downloadFile: function (fileURL) {
      var a = document.createElement('a'); a.href = fileURL; a.download = fileURL; a.style.display = 'none'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
    },

    _previewImage: function (fileID){
        var imgName = '';
        var modalHtml = '<div class="modal-img"><div class="row"><div class="col"></div><div style="text-align:right;" class="col"><span style="margin-left:auto;"><a id="OrderImgDownloadLink" href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i><span style="color:#ffffffdb !important;">Download</span></a><a style="color:#ffffffdb !important;margin-left:15px;" class="close-img">&times;</a></span></div></div><div class="row modal-img-m2m" style="height:90%;"><img class="preview-img-order" id="m2m-zoom-image" src="/web/content/' + fileID + '"/></div><div class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"><button title="Zoom In" id="m2m-zoom-in"><i class="fa fa-fw fa-plus" role="img" aria-label="Zoom In"></i></button><button title="Zoom Out" id="m2m-zoom-out"><i class="fa fa-fw fa-minus" role="img" aria-label="Zoom Out"></i></button><a href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><a target="_blank" href="/web/content/' + fileID + '"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a></div></div></div>';
        $('body').append(modalHtml);
        $('.modal-img').show();
        $('.close-img').click(function() { $('.modal-img').remove(); });
        $('.modal-img').click(function(event) { if ($(event.target).hasClass('modal-img-m2m')) { $('.modal-img').remove(); } });
        var zoomValue = 100;
        var zoomIncrement = 10;
        var minZoom = 50;
        var maxZoom = 200;
        var zoomImage = document.getElementById('m2m-zoom-image');
        var zoomInButton = document.getElementById('m2m-zoom-in');
        var zoomOutButton = document.getElementById('m2m-zoom-out');

        function updateZoomLevel() { zoomImage.style.transform = 'scale(' + (zoomValue / 100) + ')'; }
        function handleZoomIn() { if (zoomValue < maxZoom) { zoomValue += zoomIncrement; updateZoomLevel(); } }
        function handleZoomOut() { if (zoomValue > minZoom) { zoomValue -= zoomIncrement; updateZoomLevel(); } }
        zoomInButton.addEventListener('click', handleZoomIn);
        zoomOutButton.addEventListener('click', handleZoomOut);
    },
     _previewVideo: function (fileID){
        var imgName = '';
        var modalHtml = '<div class="modal-img"><div class="row"><div class="col"></div><div style="text-align:right;" class="col"><span style="margin-left:auto;"><a id="OrderImgDownloadLink" href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i><span style="color:#ffffffdb !important;">Download</span></a><a style="color:#ffffffdb !important;margin-left:15px;" class="close-img">&times;</a></span></div></div><div class="row modal-img-m2m" style="height:90%;"><video class="odx_video"><source src="/web/content/' + fileID + '" /></video></div><div class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"><button title="Play/Pause" id="m2m-play-pause"><i class="fa fa-fw"  id="icon_ply_pause" role="img" aria-label="Play/Pause"></i></button><button title="Backward 5 seconds" id="m2m-backward"><i class="fa fa-fw fa-backward" role="img" aria-label="Backward 5 seconds"></i></button><button title="Forward 5 seconds" id="m2m-forward"><i class="fa fa-fw fa-fast-forward" role="img" aria-label="Forward 5 seconds"></i></button><a href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><a target="_blank" href="/web/content/' + fileID + '"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a></div></div></div>';

        $(document).ready(function(){
          var video = document.querySelector('video');
          video.play();
          var playPauseButton = document.getElementById('m2m-play-pause');
          var forwardButton = document.getElementById('m2m-forward');
          var backwardButton = document.getElementById('m2m-backward');

        playPauseButton.addEventListener('click', function() {
            var playPause = document.getElementById('icon_ply_pause');
            if (video.paused) {
                video.play();
                playPause.classList.remove('fa-play');
                playPause.classList.add('fa-pause');
            } else {
                video.pause();
                playPause.classList.remove('fa-pause');
                playPause.classList.add('fa-play');
            }
        });
          forwardButton.addEventListener('click', function() {
            video.currentTime += 5;
          });

          backwardButton.addEventListener('click', function() {
            video.currentTime -= 5;
          });
        });
        $('body').append(modalHtml);
        $('.modal-img').show();
        $('.close-img').click(function() { $('.modal-img').remove(); });
        $('.modal-img').click(function(event) { if ($(event.target).hasClass('modal-img-m2m')) { $('.modal-img').remove(); } });
        $(document).ready(function(){
          var playPauseButton = document.getElementById('icon_ply_pause');

          var video = document.querySelector('video');
          video.play();
          playPauseButton.classList.add('fa-pause');
        });
    },

    _previewPDF: function (fileSrc) {
      var fileName = '';
      var currentPage = 1;
      var totalPageCount = 0;

      var modalHtml = '<div class="modal-pdf modal-img">' +
        '<div class="row">' +
        '<div style="text-align:center;" class="col-12">' +
        '<span id="pageCount" style="line-height:40px;color:#ffffffdb !important;">'+totalPageCount+' Page</span>' +
        '<span style="float:right;">' +
        '<a id="OrderPdfDownloadLink" href="/web/content/' + fileSrc + '" download="/web/content/' + fileName + '">' +
        '<i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i>' +
        '<span style="color:#ffffffdb !important;">Download</span></a>' +
        '<a style="color:#ffffffdb !important;margin-left:15px;" class="close-pdf">&times;</a></span></div></div>' +
        '<div class="pdf-container">' +
        '<div id="pdfCanvasContainer"></div>' +
        '</div>' +
        '<div style="position:fixed;bottom:30px;" class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"><button title="Zoom In" id="m2m-zoom-in"><i class="fa fa-fw fa-plus" role="img" aria-label="Zoom In"></i></button><button title="Zoom Out" id="m2m-zoom-out"><i class="fa fa-fw fa-minus" role="img" aria-label="Zoom Out"></i></button><a href="/web/content/' + fileSrc + '" download="/web/content/'+fileSrc+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><button title="Print" id="m2m-print-pdf"><i class="fa fa-fw fa-print" role="img" aria-label="Print"></i></button><a href="/web/content/' + fileSrc + '" target="_blank"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a></div></div></div>';
      $('body').append(modalHtml);
      $('.modal-pdf').show();
      var pdfjsLib = window['pdfjs-dist/build/pdf'];
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.10.377/pdf.worker.min.js';
      var pdfCanvasContainer = document.getElementById('pdfCanvasContainer');
      pdfjsLib.getDocument('/web/content/' + fileSrc)
        .promise
        .then(pdf => {
          totalPageCount = pdf.numPages;
          var renderPage = function(pageNum) {
            pdf.getPage(pageNum)
              .then(page => {
                var viewport = page.getViewport({ scale: 1 });
                var canvas = document.createElement('canvas');
                canvas.className = 'pdf-page-canvas';
                pdfCanvasContainer.appendChild(canvas);
                var context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                page.render({ canvasContext: context, viewport: viewport })
                  .promise
                  .then(() => {
                    currentPage = pageNum;
                    $('#pageCount').text(totalPageCount + ' Page');
                    pdfCanvasContainer.appendChild(document.createElement('br'));
                    if (pageNum < totalPageCount) { renderPage(pageNum + 1); }
                  })
                  .catch(error => {
                    console.error('Error rendering page:', error);
                  });
              })
              .catch(error => {
                console.error('Error getting page:', error);
              });
          };
          renderPage(1);
        })
        .catch(error => {
          console.error('Error:', error);
        });

      $('.close-pdf').click(function () { $('.modal-pdf').remove(); });
      $('.modal-pdf').click(function (event) { if ($(event.target).hasClass('modal-pdf')) { $('.modal-pdf').remove(); } });
      $(document).click(function (event) { if (!$(event.target).closest('#pdfCanvas').length && (event.target.tagName == 'DIV')) { $('.modal-pdf').remove(); } });

    var zoomValue = 100;
        var zoomIncrement = 10;
        var minZoom = 50;
        var marTop = 10;
        var maxZoom = 200;
        var zoomImage = document.getElementById('pdfCanvasContainer');
        var zoomInButton = document.getElementById('m2m-zoom-in');
        var zoomOutButton = document.getElementById('m2m-zoom-out');
        var printButton = document.getElementById('m2m-print-pdf');

        function updateZoomLevel() { zoomImage.style.transform = 'scale(' + (zoomValue / 100) + ')'; }
        function handleZoomIn() { if (zoomValue < maxZoom) { marTop = marTop + 10; zoomValue += zoomIncrement; updateZoomLevel(); zoomImage.style.marginTop = marTop.toString() +'%'; } }
        function handleZoomOut() { if (zoomValue > minZoom) { marTop = marTop - 10; zoomValue -= zoomIncrement; updateZoomLevel(); zoomImage.style.marginTop = marTop.toString() +'%'; } }
        zoomInButton.addEventListener('click', handleZoomIn);
        zoomOutButton.addEventListener('click', handleZoomOut);
        printButton.addEventListener('click', printPDF);
        function printPDF() { var url = '/web/content/' + fileSrc; const iframe = document.createElement('iframe'); iframe.src = url; iframe.style.display = 'none'; document.body.appendChild(iframe); iframe.onload = () => { iframe.contentWindow.focus(); iframe.contentWindow.print(); }; }
        },

})
Many2ManyBinaryField.template = "odx_m2m_attachment_preview.Many2ManyBinaryField";
registry.category("fields").add("many2many_attachment_preview", Many2ManyBinaryField);
