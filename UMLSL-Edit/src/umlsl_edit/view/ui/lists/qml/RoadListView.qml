import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
    anchors.fill: parent
    spacing: 8
    model: data_model

    delegate: ListRowDelegate {
        onEditClicked: data_model.handle_button_click(index)

        Text {
            text: model.role_name
            color: "#F9F9F9"
            font.bold: true
            font.pixelSize: 20
            Layout.minimumWidth: 0
            Layout.maximumWidth: 100
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        // 2. The Road Icon
        Image {
            source: "../../../widgets/qt_widgets/icons/add_road.svg"
            sourceSize.width: 16; sourceSize.height: 16
            rotation: model.role_isRotated ? 0 : 90

            // Good practice: Ensure the layout knows the size and alignment
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: model.role_value
            color: "#F9F9F9"
            font.pixelSize: 20
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
    }
}