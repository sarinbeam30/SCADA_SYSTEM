function bytesToString(buffer) {
    return String.fromCharCode.apply(null, new Uint8Array(buffer));
}

function stringToBytes(string) {
    var array = new Uint8Array(string.length);
    for (var i = 0, l = string.length; i < l; i++) {
        array[i] = string.charCodeAt(i);
    }
    return array.buffer;
}

var SERVICE_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E';
var TX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E';
var RX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E';

// onSuccess Callback
// This method accepts a Position object, which contains the
// current GPS coordinates
//
var onSuccess = function(position) {
    alert('Latitude: '          + position.coords.latitude          + '\n' +
            'Longitude: '         + position.coords.longitude         + '\n' +
            'Altitude: '          + position.coords.altitude          + '\n' +
            'Accuracy: '          + position.coords.accuracy          + '\n' +
            'Altitude Accuracy: ' + position.coords.altitudeAccuracy  + '\n' +
            'Heading: '           + position.coords.heading           + '\n' +
            'Speed: '             + position.coords.speed             + '\n' +
            'Timestamp: '         + position.timestamp                + '\n');
};
// onError Callback receives a PositionError object
//
function onError(error) {
    alert('code: '    + error.code    + '\n' +
            'message: ' + error.message + '\n');
}




var app = {
    
    initialize: function() {
        this.bindEvents();
    },
    bindEvents: function() {
        document.addEventListener('deviceready', this.onDeviceReady, false);
        sendButton.addEventListener('touchstart', this.updateCharacteristicValue, false);
    },
    onDeviceReady: function() {
        var property = blePeripheral.properties;
        var permission = blePeripheral.permissions;

        blePeripheral.onWriteRequest(app.didReceiveWriteRequest);
        blePeripheral.onBluetoothStateChange(app.onBluetoothStateChange);

        app.createServiceJSON();

    },
    createService: function() {
        var property = blePeripheral.properties;
        var permission = blePeripheral.permissions;

        Promise.all([
            blePeripheral.createService(SERVICE_UUID),
            blePeripheral.addCharacteristic(SERVICE_UUID, TX_UUID, property.WRITE, permission.WRITEABLE),
            blePeripheral.addCharacteristic(SERVICE_UUID, RX_UUID, property.READ | property.NOTIFY, permission.READABLE),
            blePeripheral.publishService(SERVICE_UUID),
            blePeripheral.startAdvertising(SERVICE_UUID, 'UART')
        ]).then(
            function() { console.log ('Created UART Service'); },
            app.onError
        );

        blePeripheral.onWriteRequest(app.didReceiveWriteRequest);
    },
    createServiceJSON: function() {
        var property = blePeripheral.properties;
        var permission = blePeripheral.permissions;

        var uartService = {
            uuid: SERVICE_UUID,
            characteristics: [
                {
                    uuid: TX_UUID,
                    properties: property.WRITE,
                    permissions: permission.WRITEABLE,
                    descriptors: [
                        {
                            uuid: '2901',
                            value: 'Transmit'
                        }
                    ]
                },
                {
                    uuid: RX_UUID,
                    properties: property.READ | property.NOTIFY,
                    permissions: permission.READABLE,
                    descriptors: [
                        {
                            uuid: '2901',
                            value: 'Receive'
                        }
                    ]
                }
            ]
        };

        Promise.all([
            blePeripheral.createServiceFromJSON(uartService),
            blePeripheral.startAdvertising(uartService.uuid, 'UART')
        ]).then(
            function() { console.log ('Created UART Service'); },
            app.onError
        );
    },
    updateCharacteristicValue: function() {
        var input = document.querySelector('input');
        var bytes = stringToBytes(input.value);
        var location = "";
        
        var success = function() {
            
            location = navigator.geolocation.getCurrentPosition(onSuccess, onError);
            outputDiv.innerHTML += messageInput.value + '<br/>';
            outputDiv.innerHTML += location + '<br/>'
            console.log('Updated RX value to ' + input.value);
        };
        var failure = function() {
            console.log('Error updating RX value.');
        };

        blePeripheral.setCharacteristicValue(SERVICE_UUID, RX_UUID, bytes).
            then(success, failure);

    },
    didReceiveWriteRequest: function(request) {
        var message = bytesToString(request.value);
        console.log(message);
        outputDiv.innerHTML += '<i>' + message + '</i><br/>';
    },
    onBluetoothStateChange: function(state) {
        console.log('Bluetooth State is', state);
        outputDiv.innerHTML += 'Bluetooth  is ' +  state + '<br/>';
    }
};

app.initialize();