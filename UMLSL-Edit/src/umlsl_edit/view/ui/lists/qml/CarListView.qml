import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
    anchors.fill: parent
    spacing: 8
    model: data_model

    delegate: ListRowDelegate {
        onEditClicked: data_model.handle_button_click(index)
        border_color: model.role_color

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

        Text {
            text: model.role_value
            color: "#F9F9F9"
            font.pixelSize: 20

            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
    }
}