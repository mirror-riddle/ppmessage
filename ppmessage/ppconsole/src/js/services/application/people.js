//// this is data service for `ApplicationPeopleCtrl` ///////
(function() {

    yvAppPeopleService.$inject = [ 'yvAjax', 'yvUser', 'yvCallbackService', 'yvDebug' ];
    function yvAppPeopleService( yvAjax, yvUser, yvCallbackService, yvDebug ) {

        var DEFAULT_PAGE_COUNT = 12, jQuery = $;
        
        ////// Api //////////

        return {
            getAppServiceUsers: getAppServiceUsers,
            getAppServiceUsersWithPagination: getAppServiceUsersWithPagination,
            createServiceUser: createServiceUser
        }

        ////// Implementation //////////

        function getAppServiceUsers( successCallback, errorCallback ) {
            
            yvAjax.get_team_service_user_list( { app_uuid: yvUser.get_team().uuid } ).then( function( response ) {
                yvCallbackService.response( angular.copy(response), onSuccess, onError );
            }, onError );
            
            function onSuccess( data ) {
                var appTeamServiceUsers = data.list || [];
                angular.forEach( appTeamServiceUsers, function( value, index ) {
                    value.is_owner_user = ( value.user_email === yvUser.get_email() );
                } );
                successCallback && successCallback( appTeamServiceUsers );
            }

            function onError( e ) {
                errorCallback && errorCallback( [] );
            }
            
        }

        // @description
        //     - filter by user_fullname or user_email
        //     - support pagination ( in front-end )
        //     - support sort by `updatetime`
        //
        // @param settings
        // {
        //     length: `count of each page`, default is 12
        //     start_page: 0 ~ +Infinity
        //     
        //     filter_keyword: `your keyword`, default is ''
        //     sort: `true/false`, default is `true`, sort by `updatetime` in Desending order
        // }
        //
        // @return
        // {
        //     users: [ userA, userB, ... ], // current page users
        //     total: totalNumber // total user's count after filtered
        // }
        function getAppServiceUsersWithPagination( settings, successCallback, errorCallback ) {
            getAppServiceUsers( function( users ) {
                
                // `angular.extend(dst, src);`
                // @see http://docs.angularjs.cn/api/ng/function/angular.extend
                var s = angular.extend( { filter_keyword: '', length: DEFAULT_PAGE_COUNT, start_page: 0, sort: true }, settings ),
                    filteredUsers = filter( s, users ),
                    total = filteredUsers.length,
                    paginationUsers = pagination( s, sort( s, filteredUsers ) );
                
                yvCallbackService.success( {
                    users: paginationUsers,
                    total: total
                } , successCallback );
                
            }, function( e ) {
                yvCallbackService.error( e, errorCallback );
            } );
        }

        function createServiceUser( settings, successCallback, errorCallback ) {
            getAppServiceUsers( function( users ) {
                yvAjax.create_user( settings ).then( successCallback, errorCallback );
            }, function( e ) {
                yvCallbackService.error( e, errorCallback );
            } );
        }

        function filter( settings, users ) {
            
            if ( settings.filter_keyword === '' ) {
                return users || [];
            }

            var keyword = settings.filter_keyword,
                regex = new RegExp( '.*' + keyword + '.*', 'g' ),
                result = [];
            
            angular.forEach( users, function( value, index ) {
                if ( regex.test( value.user_email ) || regex.test( value.user_fullname ) ) {
                    result.push( value );
                }
            } );

            return result;
        }

        function pagination( settings, users ) {
            var pageCount = settings.length,
                pageNum = settings.start_page,
                len = users.length,
                startIndex = pageNum * pageCount,
                endIndex = startIndex + pageCount,
                i = startIndex,
                result = [];

            var user;
            while ( ( user = users [ i++ ] ) !== undefined && i <= endIndex ) {
                result.push( user );
            }
            return result;            
        }

        function sort( settings, users ) {
            if ( !settings.sort ) return users;
            return users.sort( compare );
            function compare( a, b ) {
                return a.updatetime > b.updatetime ? -1 : 1;
            }
        }
    }

    angular.module("this_app.services").factory("yvAppPeopleService", yvAppPeopleService);

} )();
