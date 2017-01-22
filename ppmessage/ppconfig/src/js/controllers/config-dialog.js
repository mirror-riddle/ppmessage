function ConfigServerController($scope, $mdDialog, yvAjax) {

    $scope.server = {

        url: "http://" + $scope._config_status.ip + ":8945",

        identicon_store: "/usr/local/opt/ppmessage/identicon",
        generic_store: "/usr/local/opt/ppmessage/generic",

        disable_submit: false
    };

    $scope.hide = function() {
        $mdDialog.hide();
    };

    $scope.cancel = function() {
        $mdDialog.cancel();
    };
    
    $scope.answer = function(answer) {
        $mdDialog.hide(answer);
    };

    $scope.confirm = function() {
        $scope.server.disable_submit = true;
        yvAjax.server($scope.server).then(function() {
            $mdDialog.hide("success");
        }, function() {
            $scope.server.disable_submit = false;
            console.log("server config failed");
        });
    };    
}

function ConfigDatabaseController($scope, $mdDialog, yvAjax) {

    var DATABASE_TYPE = {
        SQLITE: "SQLITE",
        MYSQL: "MYSQL",
        PGSQL: "PGSQL"
    };

    $scope.database = {
        type: DATABASE_TYPE.SQLITE,
        types: angular.copy(DATABASE_TYPE),
        sqlite: {
            db_file_path: "/usr/local/var/db/sqlite/ppmessage.db"
        },
        mysql: {
            db_host: "127.0.0.1",
            db_port: "3306",
            db_user: "root",
            db_pass: "test",
            db_name: "ppmessage"
        },

        pgsql: {
            db_host: "127.0.0.1",
            db_port: "5432",
            db_user: "postgres",
            db_pass: "test",
            db_name: "ppmessage"
        },

        disable_submit: false
    };

    $scope.hide = function() {
        $mdDialog.hide();
    };

    $scope.cancel = function() {
        $mdDialog.cancel();
    };
    
    $scope.answer = function(answer) {
        $mdDialog.hide(answer);
    };

    $scope.should_show_mysql = function() {
        if ($scope.database.type == DATABASE_TYPE.MYSQL) {
            return true;
        }
        return false;
    };

    $scope.should_show_sqlite = function() {
        if ($scope.database.type == DATABASE_TYPE.SQLITE) {
            return true;
        }
        return false;
    };

    $scope.should_show_pgsql = function() {
        if ($scope.database.type == DATABASE_TYPE.PGSQL) {
            return true;
        }
        return false;
    };

    $scope.confirm = function() {
        $scope.database.disable_submit = true;
        yvAjax.database($scope.database).then(function() {
            $mdDialog.hide("success");
        }, function() {
            $scope.database.disable_submit = false;
            console.log("database config failed");
        });
    };
}

function CreateFirstController($scope, $mdDialog, yvAjax) {
    
    $scope.user = {
        user_status: "OWNER_2",
        user_fullname: "Guijin Ding",
        user_email: "dingguijin@gmail.com",
        user_password: "x",
        team_name: "PPMessage",

        user_password_is_visible: false,
        password_input_type: "password",

        disable_submit: false
    };

    $scope.hide = function() {
        $mdDialog.hide();
    };

    $scope.cancel = function() {
        $mdDialog.cancel();
    };
    
    $scope.answer = function(answer) {
        $mdDialog.hide(answer);
    };

    $scope.confirm = function() {
        $scope.user.disable_submit = true;
        yvAjax.first($scope.user).then(function(){
            $mdDialog.hide("success");
        }, function(){
            $scope.user.disable_submit = false;
            console.log("first user create failed");
        });
    };
    
    $scope.show_user_password = function(show) {
        if (show) {
            $scope.user.user_password_is_visible = true;
            $scope.user.password_input_type = "text";
        } else {
            $scope.user.user_password_is_visible = false;
            $scope.user.password_input_type = "password";
        }
    };

}

function RestartController($scope, $mdDialog, yvAjax) {
    $scope.user = {
        user_password: "",
    
        user_password_is_visible: false,
        password_input_type: "password",

        disable_submit: false
    };

    $scope.hide = function() {
        $mdDialog.hide();
    };

    $scope.cancel = function() {
        $mdDialog.cancel();
    };
    
    $scope.answer = function(answer) {
        $mdDialog.hide(answer);
    };

    $scope.confirm = function() {
        $scope.user.disable_submit = true;
        yvAjax.restart($scope.user).then(function() {
            $mdDialog.hide("success");
        }, function(){
            $scope.user.disable_submit = false;
        });
    };

    $scope.pass = function() {
        $mdDialog.hide("success");
    };

    $scope.show_user_password = function(show) {
        if (show) {
            $scope.user.user_password_is_visible = true;
            $scope.user.password_input_type = "text";
        } else {
            $scope.user.user_password_is_visible = false;
            $scope.user.password_input_type = "password";
        }
    };

}
    

