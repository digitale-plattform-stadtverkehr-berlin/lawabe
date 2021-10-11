var editableLayers = new L.FeatureGroup();

jQuery(document).ready(function () {
    if ($("#map").length > 0) {
        const center = [52.5, 13.4];
        let fmap = L.map("map").setView(center, 11);
        L.tileLayer.wms("https://isk.geobasis-bb.de/mapproxy/webatlasde/service/wms?", {
            layers: "WebAtlasDE_BEBB_halbton",
            attribution: "© GeoBasis-DE/LGB,&nbsp;<a href=\"https://www.govdata.de/dl-de/by-2-0\" target=\"_blank\">dl-de/by-2-0</a>, Daten geändert"
        }).addTo(fmap);
        editableLayers.addTo(fmap)


        var drawPluginOptions = {
            position: 'topright',
            draw: {
                polygon: false,
                polyline: {
                    shapeOptions: {
                        clickable: false,
                        color: '#FF0000'
                    },
                    showLength: false
                },
                rectangle: false,
                circle: false,
                marker: {},
                circlemarker: false
            },
            edit: {
                featureGroup: editableLayers,
                edit: {
                    selectedPathOptions: {
                        fillColor: '#3278B9',
                        fillOpacity: 0.2,
                    }
                },
                remove: false
            }
        };

        L.drawLocal = {
            draw: {
                toolbar: {
                    actions: {
                        title: 'Abbrechen',
                        text: 'Abbrechen'
                    },
                    finish: {
                        title: 'Beenden',
                        text: 'Beenden'
                    },
                    undo: {
                        title: 'Rückgängig',
                        text: 'Rückgängig'
                    },
                    buttons: {
                        rectangle: 'Raumbezug erstellen',
                    }
                },
                handlers: {
                    simpleshape: {tooltip: {}},
                    polygon: false,
                    polyline: {tooltip: {}},
                    rectangle: {
                        tooltip: {
                            start: 'Klicken und ziehen.',
                        }
                    },
                    circle: {tooltip: {}},
                    marker: {tooltip: {}},
                    circlemarker: {tooltip: {}},
                }
            },
            edit: {
                toolbar: {
                    actions: {
                        save: {
                            title: 'Übernehmen',
                            text: 'Übernehmen'
                        },
                        cancel: {
                            title: 'Abbrechen',
                            text: 'Abbrechen'
                        },
                        clearAll: {
                            title: 'Entfernen',
                            text: 'Entfernen'
                        }
                    },
                    buttons: {
                        edit: 'Raumbezug bearbeiten',
                        editDisabled: 'Kein Raumbezug zum ändern vorhanden',
                        remove: 'Raumbezug entfernen',
                        removeDisabled: 'Kein Raumbezug zum ändern vorhanden'
                    }
                },
                handlers: {
                    edit: {
                        tooltip: {
                            text: 'Raumbezug verändern über Eckpunkte oder verschieben über Mittelpunkt',
                            subtext: ''
                        }
                    },
                    remove: {
                        tooltip: {
                            text: 'Raumbezug anklicken zum entfernen.'
                        }
                    },
                }
            }
        };

        // Initialise the draw control and pass it the FeatureGroup of editable layers
        drawControl = new L.Control.Draw(drawPluginOptions);
        fmap.addControl(drawControl);

        fmap.on('draw:created', function (e) {
            var layer = e.layer;

            saveSpatial(layer);

            editableLayers.clearLayers();
            editableLayers.addLayer(layer);
        });
        fmap.on('draw:editstop ', function (e) {
            saveSpatial(editableLayers.getLayers()[0]);
        });
        fmap.on('draw:drawstart', function (e) {
            $(".leaflet-draw-actions").hide();
        });

        const spatialString = $("#spatial")[0].value
        if(spatialString !== undefined && spatialString.trim().length !== 0) {
            var coords = JSON.parse(spatialString);
            for(var i = 0; i < coords.length; i++){
                coord = coords[i];
                lng = coord[0];
                lat = coord[1];
                coord[0] = lat;
                coord[1] = lng;
            }
            if (coords.length > 1) {
                editableLayers.addLayer(L.polyline(coords, {color: 'red'}));
            }
            else if (coords.length == 1)
                editableLayers.addLayer(L.marker(coords[0]));
        }
    }

    if ($("#valid-from").length > 0 && $("#valid-to").length > 0) {
        var options = {
            enableTime: true,
            dateFormat: "Y-m-d\\TH:i",
            altInput: true,
            altFormat: "d.m.Y H:i",
            time_24hr: true,
        };
        $("#valid-from").flatpickr(options);
        $("#valid-to").flatpickr(options);
    }
});

function coordsToString(coords) {
    var result = "["
    for (var i = 0; i < coords.length; i++) {
        if (i > 0) result += ","
        var coord = coords[i];
        result += "[" + coord.lng + "," + coord.lat + "]"
    }
    result += "]";

    return result;
}

function saveSpatial(layer) {
    var coords = "";

    if (typeof layer.getLatLng === 'function') {
        coords = coordsToString([layer.getLatLng()]);
    } else if (typeof layer.getLatLngs === 'function') {
        coords = coordsToString(layer.getLatLngs());
    }
    $("#spatial")[0].value = coords;
}
