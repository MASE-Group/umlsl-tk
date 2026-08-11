import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    signal editClicked()

    default property alias content: contentArea.data
    property color border_color: "#032F40"

    width: ListView.view.width
    height: 44

    color: model.role_is_selected ? "#032F40" : "#011C26"

    border.color: border_color
    border.width: 2
    radius: 16

    // --- 2. Background Selection Handler ---
    // This sits at the bottom of the stack (defined first).
    // Any click NOT caught by a button on top will fall through to here.
    MouseArea {
        anchors.fill: parent
        onClicked: {
            // Helper function to handle selection via the C++ model
            root.ListView.view.model.select_row(index)
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        anchors.topMargin: 0
        anchors.bottomMargin: 0
        spacing: 4

        RowLayout {
            id: contentArea
            Layout.fillWidth: true
            spacing: 8
        }

        // --- The Edit Button ---
        Rectangle {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            radius: 16

            // Button visual states
            color: editMouseArea.pressed ? "transparent" : (editMouseArea.containsMouse ? "#084D68" : "transparent")
            opacity: editMouseArea.enabled ? 1.0 : 0.4
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

            Image {
                anchors.centerIn: parent
                source: "../../../widgets/qt_widgets/icons/edit.svg"
                sourceSize.width: 16; sourceSize.height: 16
            }

            MouseArea {
                id: editMouseArea
                anchors.fill: parent
                enabled: !model.role_loading
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                hoverEnabled: enabled
                onClicked: root.editClicked()
            }
        }
    }
}
